"""Bounded JQL-like grammar compiled only to allowlisted WorkItem ORM fields."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from functools import reduce
import json
import re

from django.db.models import Case, IntegerField, Q, Value, When, F
from django.utils import timezone

from spaces.models import SpaceTask
from spaces.services import visible_spaces


class QueryError(ValueError):
    pass


ALIASES = {'project': 'space', 'issuetype': 'type', 'work_type': 'type', 'labels': 'tag',
           'tags': 'tag', 'summary': 'text', 'duedate': 'due', 'statuscategory': 'category'}
FIELDS = {'space', 'status', 'priority', 'type', 'assignee', 'reporter', 'tag', 'key',
          'text', 'due', 'created', 'team', 'sprint', 'category'}
SORT_FIELDS = {'created': 'task__created_at', 'due': 'task__due_at', 'key': 'key',
               'priority': '_filter_priority', 'summary': 'task__title', 'status': 'status'}
TOKEN = re.compile(r'\s*(?:"((?:\\.|[^"\\])*)"|\'((?:\\.|[^\'\\])*)\'|(!=|!~|>=|<=|[=~><(),])|([^\s(),=!<>~"\']+))')
DEFAULT_ORDER = [('created', 'DESC')]


def quote(value):
    return json.dumps(str(value), ensure_ascii=False)


@dataclass
class SearchQuery:
    expression: object
    order: list

    def basic(self):
        """Return basic controls only when conversion preserves the whole query."""
        values = {}

        def visit(node):
            if node is None:
                return True
            if node[0] == 'or' and node[2] == ('clause', 'assignee', 'IS EMPTY', []):
                if node[1][0:3] != ('clause', 'assignee', 'IN') or 'assignee' in values:
                    return False
                if not visit(node[1]):
                    return False
                values['assignee'].append('unassigned')
                return True
            if node[0] == 'and':
                return visit(node[1]) and visit(node[2])
            if node[0] != 'clause':
                return False
            _, field, operator, operands = node
            if field not in {'space', 'status', 'priority', 'type', 'assignee', 'tag', 'team', 'text'} or field in values:
                return False
            if field == 'text':
                if operator != '~':
                    return False
                values['q'] = operands[0]
            elif operator in {'=', 'IN'}:
                values[field] = ['me' if value == ('function', 'currentuser') else value for value in operands]
            elif field == 'assignee' and operator == 'IS EMPTY':
                values[field] = ['unassigned']
            else:
                return False
            return True

        if not visit(self.expression) or len(self.order) != 1:
            return None
        field, direction = self.order[0]
        sort = f'{field.lower()}_{direction.lower()}'
        if sort not in BASIC_SORTS:
            return None
        values['sort'] = sort
        return values


BASIC_SORTS = {'created_desc': 'Najnowsze', 'created_asc': 'Najstarsze', 'key_asc': 'Klucz',
               'due_asc': 'Termin', 'priority_desc': 'Priorytet', 'summary_asc': 'Temat'}


class Parser:
    def __init__(self, source):
        if len(source) > 4000:
            raise QueryError('Zapytanie może mieć maksymalnie 4000 znaków.')
        self.tokens = []
        position = 0
        while position < len(source.rstrip()):
            match = TOKEN.match(source, position)
            if not match:
                raise QueryError(f'Nieprawidłowy znak na pozycji {position + 1}.')
            double, single, symbol, word = match.groups()
            if double is not None or single is not None:
                raw = double if double is not None else single
                try:
                    value = json.loads('"' + raw + '"') if double is not None else re.sub(r'\\(.)', r'\1', raw)
                except ValueError:
                    raise QueryError('Nieprawidłowy tekst w cudzysłowie.') from None
                kind = 'string'
            else:
                value, kind = (symbol, 'symbol') if symbol else (word, 'word')
            self.tokens.append((kind, value))
            position = match.end()
        if len(self.tokens) > 600:
            raise QueryError('Zapytanie jest zbyt złożone.')
        self.index = 0
        self.depth = 0

    def is_token(self, value):
        return self.index < len(self.tokens) and self.tokens[self.index][0] != 'string' and self.tokens[self.index][1].upper() == value

    def take(self, value):
        if self.is_token(value):
            self.index += 1
            return True
        return False

    def expect(self, value):
        if not self.take(value):
            raise QueryError(f'Oczekiwano „{value}” (element {self.index + 1}).')

    def value(self):
        if self.index >= len(self.tokens) or self.tokens[self.index][0] == 'symbol':
            raise QueryError('Podaj wartość warunku.')
        kind, value = self.tokens[self.index]
        if kind == 'word' and value.upper() in {'AND', 'OR', 'NOT', 'IN', 'IS', 'ORDER', 'BY', 'ASC', 'DESC'}:
            raise QueryError('Wartości zawierające słowa składni otocz cudzysłowem.')
        self.index += 1
        if kind == 'word' and self.take('('):
            name = value.lower()
            if name not in {'currentuser', 'startofday'}:
                raise QueryError('Obsługiwane funkcje: currentUser() i startOfDay().')
            self.expect(')')
            return ('function', name)
        return value

    def atom(self):
        self.depth += 1
        if self.depth > 20:
            raise QueryError('Zbyt wiele zagnieżdżonych warunków.')
        try:
            if self.take('NOT'):
                return ('not', self.atom())
            if self.take('('):
                node = self.expression()
                self.expect(')')
                return node
            field = self.value()
            if not isinstance(field, str):
                raise QueryError('Podaj nazwę pola.')
            field = ALIASES.get(field.lower(), field.lower())
            if field not in FIELDS:
                raise QueryError(f'Nieobsługiwane pole: {field}.')
            if self.take('IS'):
                negate = self.take('NOT')
                self.expect('EMPTY')
                return ('clause', field, 'IS NOT EMPTY' if negate else 'IS EMPTY', [])
            negate = self.take('NOT')
            if self.take('IN'):
                self.expect('(')
                values = [self.value()]
                while self.take(','):
                    values.append(self.value())
                    if len(values) > 100:
                        raise QueryError('Lista może zawierać maksymalnie 100 wartości.')
                self.expect(')')
                return ('clause', field, 'NOT IN' if negate else 'IN', values)
            if negate:
                raise QueryError('Po NOT oczekiwano IN.')
            for operator in ('=', '!=', '~', '!~', '>=', '<=', '>', '<'):
                if self.take(operator):
                    return ('clause', field, operator, [self.value()])
            raise QueryError('Podaj operator: =, !=, IN, NOT IN, ~, !~, IS EMPTY lub porównanie dat.')
        finally:
            self.depth -= 1

    def conjunction(self):
        node = self.atom()
        while self.take('AND'):
            node = ('and', node, self.atom())
        return node

    def expression(self):
        node = self.conjunction()
        while self.take('OR'):
            node = ('or', node, self.conjunction())
        return node

    def parse(self):
        node = None if not self.tokens or self.is_token('ORDER') else self.expression()
        order = list(DEFAULT_ORDER)
        if self.take('ORDER'):
            self.expect('BY')
            order = []
            while True:
                field = self.value()
                if not isinstance(field, str) or field.lower() not in SORT_FIELDS:
                    raise QueryError('Sortowanie: created, due, key, priority, summary lub status.')
                direction = 'DESC' if self.take('DESC') else 'ASC'
                if direction == 'ASC':
                    self.take('ASC')
                order.append((field.lower(), direction))
                if len(order) > 6:
                    raise QueryError('Można sortować według maksymalnie 6 pól.')
                if not self.take(','):
                    break
        if self.index != len(self.tokens):
            raise QueryError(f'Nieoczekiwany element: {self.tokens[self.index][1]}.')
        return SearchQuery(node, order)


def parse_query(source):
    return Parser(source.strip()).parse()


def date_value(value, now):
    if value == ('function', 'startofday'):
        return timezone.make_aware(datetime.combine(timezone.localdate(now), time.min)), False
    if not isinstance(value, str):
        raise QueryError('Dla dat użyj YYYY-MM-DD, względnego czasu (np. -7d) lub startOfDay().')
    relative = re.fullmatch(r'([+-]?\d{1,4})([dhwm])', value.lower())
    if relative:
        amount, unit = relative.groups()
        return now + timedelta(seconds=int(amount) * {'d': 86400, 'h': 3600, 'w': 604800, 'm': 60}[unit]), False
    try:
        parsed = datetime.fromisoformat(value)
        if not 1900 <= parsed.year <= 9998:
            raise ValueError
        return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed, len(value) == 10
    except (ValueError, OverflowError):
        raise QueryError('Nieprawidłowa data. Użyj YYYY-MM-DD lub np. -7d.') from None


class Compiler:
    def __init__(self, request, now=None):
        self.request = request
        self.now = now or timezone.now()
        self.configurations = None

    def configured(self, field, value):
        if self.configurations is None:
            self.configurations = list(visible_spaces(self.request).values_list('pk', 'configuration__settings'))
        rows_key = 'statuses' if field == 'status' else 'types'
        result = Q(**{field if field == 'status' else 'work_type': value})
        for space_id, settings in self.configurations:
            for option in settings.get(rows_key, []):
                if option['label'].casefold() == value.casefold():
                    result |= Q(space_id=space_id, **{field if field == 'status' else 'work_type': option['key']})
        return result

    def equal(self, field, value):
        if field in {'assignee', 'reporter'} and value == ('function', 'currentuser'):
            return Q(**{'task__assignee_id' if field == 'assignee' else 'task__created_by_id': self.request.user.pk})
        if not isinstance(value, str):
            raise QueryError('currentUser() jest dostępne dla wykonawcy i autora; startOfDay() dla dat.')
        if field == 'space':
            return Q(space_id=int(value)) if value.isdecimal() and len(value) < 19 else Q(space__key__iexact=value) | Q(space__name__iexact=value)
        if field in {'status', 'type'}:
            return self.configured(field, value)
        if field in {'priority', 'category'}:
            choices = SpaceTask.PRIORITY_CHOICES if field == 'priority' else SpaceTask.STATUS_CHOICES
            mapping = {label.casefold(): key for key, label in choices}
            if field == 'category':
                mapping.update({'done': 'closed', 'to do': 'new', 'in progress': 'in_progress'})
            return Q(**{'task__priority' if field == 'priority' else 'task__status': mapping.get(value.casefold(), value.lower())})
        if field in {'assignee', 'reporter'}:
            path = 'task__assignee' if field == 'assignee' else 'task__created_by'
            if value.isdecimal() and len(value) < 19:
                return Q(**{path + '_id': int(value)})
            return Q(**{path + '__email__iexact': value}) | Q(**{path + '__username__iexact': value})
        if field in {'team', 'sprint', 'tag'}:
            path = 'task__tags' if field == 'tag' else field
            if field == 'tag':
                lookup = {'tags__pk': int(value)} if value.isdecimal() and len(value) < 19 else {'tags__name__iexact': value}
                # Each tag clause has its own subquery: tag=A AND tag=B means both tags.
                return Q(task_id__in=SpaceTask.objects.filter(**lookup).values('pk'))
            return Q(**{path + '__pk': int(value)}) if value.isdecimal() and len(value) < 19 else Q(**{path + '__name__iexact': value})
        if field == 'key':
            return Q(key__iexact=value)
        if field == 'text':
            return Q(task__title__iexact=value)
        raise QueryError('Nieobsługiwany warunek.')

    def clause(self, field, operator, operands):
        paths = {'assignee': 'task__assignee', 'reporter': 'task__created_by', 'due': 'task__due_at',
                 'created': 'task__created_at', 'team': 'team', 'sprint': 'sprint', 'tag': 'task__tags'}
        if operator.startswith('IS '):
            if field not in paths:
                raise QueryError('IS EMPTY jest dostępne dla wykonawcy, autora, dat, zespołu, sprintu i tagów.')
            return Q(**{paths[field] + '__isnull': operator == 'IS EMPTY'})
        if field in {'due', 'created'}:
            if operator not in {'=', '!=', '>', '>=', '<', '<='}:
                raise QueryError('Daty obsługują =, !=, >, >=, < i <=.')
            value, whole_day = date_value(operands[0], self.now)
            path = paths[field]
            if whole_day and operator in {'=', '!='}:
                condition = Q(**{path + '__gte': value, path + '__lt': value + timedelta(days=1)})
            else:
                if whole_day and operator in {'>', '<='}:
                    value += timedelta(days=1)
                    operator = '>=' if operator == '>' else '<'
                condition = Q(**{path + '__' + {'=': 'exact', '!=': 'exact', '>': 'gt', '>=': 'gte', '<': 'lt', '<=': 'lte'}[operator]: value})
            return ~condition & Q(**{path + '__isnull': False}) if operator == '!=' else condition
        if operator in {'~', '!~'}:
            if field not in {'text', 'key'} or not isinstance(operands[0], str):
                raise QueryError('Operator ~ jest dostępny dla text, summary i key.')
            value = operands[0]
            condition = Q(key__icontains=value) if field == 'key' else Q(task__title__icontains=value) | Q(task__description__icontains=value) | Q(key__icontains=value)
            return ~condition if operator == '!~' else condition
        if operator not in {'=', '!=', 'IN', 'NOT IN'}:
            raise QueryError('Porównania >, >=, <, <= są dostępne wyłącznie dla dat.')
        condition = reduce(lambda left, right: left | right, (self.equal(field, value) for value in operands))
        if operator in {'!=', 'NOT IN'}:
            condition = ~condition
            if field in {'assignee', 'reporter', 'team', 'sprint', 'tag'}:
                condition &= Q(**{paths[field] + '__isnull': False})
        return condition

    def expression(self, node):
        if node is None:
            return Q()
        if node[0] == 'clause':
            return self.clause(*node[1:])
        if node[0] == 'not':
            return ~self.expression(node[1])
        left, right = self.expression(node[1]), self.expression(node[2])
        return left & right if node[0] == 'and' else left | right


def apply_query(request, items, source):
    query = parse_query(source)
    items = items.filter(Compiler(request).expression(query.expression)).distinct()
    if any(field == 'priority' for field, _ in query.order):
        items = items.annotate(_filter_priority=Case(
            *[When(task__priority=key, then=Value(index)) for index, (key, _) in enumerate(SpaceTask.PRIORITY_CHOICES)],
            default=Value(0), output_field=IntegerField(),
        ))
    ordering = []
    for field, direction in query.order:
        paths = ['space__key', 'number'] if field == 'key' else [SORT_FIELDS[field]]
        ordering.extend(F(path).desc(nulls_last=True) if direction == 'DESC' else F(path).asc(nulls_last=True) for path in paths)
    return items.order_by(*ordering, 'pk'), query


def basic_query(data):
    clauses = []
    if data.get('q'):
        clauses.append('text ~ ' + quote(data['q']))
    for field in ('space', 'status', 'priority', 'type', 'assignee', 'tag', 'team'):
        values = data.get(field, [])
        if not values:
            continue
        empty = field == 'assignee' and 'unassigned' in values
        operands = ['currentUser()' if field == 'assignee' and value == 'me' else quote(value) for value in values if value != 'unassigned']
        clause = f'{field} IN ({", ".join(operands)})' if operands else ''
        if empty:
            clause = f'({clause} OR assignee IS EMPTY)' if clause else 'assignee IS EMPTY'
        clauses.append(clause)
    field, direction = data.get('sort', 'created_desc').rsplit('_', 1)
    return (' AND '.join(clauses) + f' ORDER BY {field} {direction.upper()}').strip()
