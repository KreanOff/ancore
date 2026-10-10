from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from workplaces.models import Workplace, WorkplaceMembership, create_workplace_for_user
from workplaces.services import (
    ACTIVE_WORKPLACE_SESSION_KEY,
    WORKPLACE_URL_SCOPE_SESSION_KEY,
    scoped_workplace_app_path,
)


class LoginRedirectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'login-redirect-test-83!'
        cls.user = get_user_model().objects.create_user(
            username='login-redirect', email='login-redirect@example.test',
            password=cls.password,
        )

    def login(self, url=None, **extra):
        return self.client.post(url or reverse('login'), {
            'username': self.user.email, 'password': self.password, **extra,
        }, follow=True)

    def assert_for_you(self, response, expected_url=None):
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/for_you.html')
        self.assertEqual(response.redirect_chain[-1], (expected_url or reverse('for_you'), 302))
        self.assertNotIn((reverse('workplaces:workplaces'), 302), response.redirect_chain)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_first_login_opens_for_you_and_initializes_workspace(self):
        self.assertFalse(Workplace.objects.filter(owner=self.user).exists())

        response = self.login()

        self.assert_for_you(response)
        workplace = Workplace.objects.get(owner=self.user)
        self.assertEqual(response.wsgi_request.workplace, workplace)
        self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], workplace.pk)

    def test_first_login_after_registration_and_relogin_open_for_you(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Anna', 'last_name': 'Nowak',
            'email': 'registered-login@example.test',
            'password1': self.password, 'password2': self.password,
        })
        self.assertRedirects(response, reverse('login'))
        self.user = get_user_model().objects.get(email='registered-login@example.test')

        self.assert_for_you(self.login())
        workplace = Workplace.objects.get(owner=self.user)
        self.client.post(reverse('logout'))
        self.assert_for_you(self.login())
        self.assertEqual(Workplace.objects.filter(owner=self.user).count(), 1)
        self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], workplace.pk)

    def test_get_and_post_next_cannot_change_login_destination(self):
        for next_url in (
            reverse('workplaces:workplaces'), reverse('home'), reverse('tasks:tasks'),
            'https://example.test/elsewhere/', '//example.test/elsewhere/',
        ):
            for source in ('get', 'post'):
                with self.subTest(next=next_url, source=source):
                    self.client.logout()
                    if source == 'get':
                        response = self.login(f'{reverse("login")}?next={next_url}')
                    else:
                        response = self.login(next=next_url)
                    self.assert_for_you(response)

    def test_login_page_does_not_keep_next_in_form(self):
        response = self.client.get(reverse('login'), {'next': reverse('workplaces:workplaces')})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="next"')

    def test_login_keeps_active_workspace_and_scoped_destination(self):
        create_workplace_for_user(self.user, 'A pierwszy Workspace')
        selected = create_workplace_for_user(self.user, 'Z wybrany Workspace')
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = selected.pk
        session[WORKPLACE_URL_SCOPE_SESSION_KEY] = True
        session.save()

        response = self.login(next=reverse('workplaces:workplaces'))

        self.assert_for_you(response, scoped_workplace_app_path(selected, 'for-you'))
        self.assertEqual(response.wsgi_request.workplace, selected)
        self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], selected.pk)

    def test_member_login_opens_for_you_in_shared_workspace(self):
        owner = get_user_model().objects.create_user(username='shared-login-owner', email='shared-login@example.test')
        workplace = create_workplace_for_user(owner, 'Wspólny Workspace')
        WorkplaceMembership.objects.create(workplace=workplace, user=self.user, role='member')

        response = self.login()

        self.assert_for_you(response)
        self.assertEqual(response.wsgi_request.workplace, workplace)
        self.assertFalse(Workplace.objects.filter(owner=self.user).exists())

    def test_foreign_workspace_in_session_or_next_does_not_grant_access(self):
        own = create_workplace_for_user(self.user, 'Własny Workspace')
        owner = get_user_model().objects.create_user(username='foreign-login-owner', email='foreign-login@example.test')
        foreign = create_workplace_for_user(owner, 'Obcy Workspace')
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = foreign.pk
        session[WORKPLACE_URL_SCOPE_SESSION_KEY] = True
        session.save()

        response = self.login(next=scoped_workplace_app_path(foreign, 'for-you'))

        self.assert_for_you(response, scoped_workplace_app_path(own, 'for-you'))
        self.assertEqual(response.wsgi_request.workplace, own)
        self.assertEqual(self.client.session[ACTIVE_WORKPLACE_SESSION_KEY], own.pk)

    def test_wrong_password_keeps_login_form_and_anonymous_session(self):
        response = self.client.post(reverse('login'), {
            'username': self.user.email, 'password': 'wrong-password',
            'next': reverse('workplaces:workplaces'),
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'Email lub hasło są nieprawidłowe.')
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertFalse(Workplace.objects.filter(owner=self.user).exists())

    def test_login_still_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(reverse('login'), {
            'username': self.user.email, 'password': self.password,
        })

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(SESSION_KEY, client.session)
