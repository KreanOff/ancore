document.addEventListener('DOMContentLoaded', function() {
    const taskRows = document.querySelectorAll('.task-row');
    const projectRows = document.querySelectorAll('.tasks-project-row');
    const sectionRows = document.querySelectorAll('.tasks-section-row');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const editBtn = document.getElementById('edit-selected-btn');
    const statusToggleBtn = document.getElementById('status-toggle-btn');
    const selectionActions = document.getElementById('selection-actions');
    const selectedCountSpan = document.getElementById('selected-count');
    const filterStatus = document.getElementById('filter-status');
    const filterPriority = document.getElementById('filter-priority');
    const filterSearch = document.getElementById('filter-search');
    const filterButtons = document.querySelectorAll('[data-status-filter], [data-priority-filter]');
    const statusFilterMenu = document.querySelector('[data-status-filter-menu]');
    const statusFilterToggle = document.querySelector('[data-status-filter-toggle]');
    const statusFilterLabel = document.querySelector('[data-status-filter-label]');
    const statusFilterIcon = document.querySelector('[data-status-filter-icon]');
    const priorityFilterMenu = document.querySelector('[data-priority-filter-menu]');
    const priorityFilterToggle = document.querySelector('[data-priority-filter-toggle]');
    const priorityFilterLabel = document.querySelector('[data-priority-filter-label]');
    const priorityFilterIcon = document.querySelector('[data-priority-filter-icon]');
    const groupRows = document.querySelectorAll('.tasks-group-row');
    const issueGroups = document.querySelectorAll('.tasks-issue-group');
    const statusSubgroups = document.querySelectorAll('.tasks-status-subgroup');
    const collapsibleGroupHeaders = document.querySelectorAll('.tasks-issue-group-header, .tasks-status-subgroup-header');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const checkboxes = document.querySelectorAll('.task-checkbox');
    const createMenu = document.querySelector('[data-create-menu]');
    const createMenuToggle = document.getElementById('open-create-menu');
    const createMenuPanel = document.getElementById('create-menu-panel');
    const sectionActionMenu = document.querySelector('[data-section-actions]');
    const projectActionMenus = document.querySelectorAll('[data-project-actions]');
    const projectTree = document.querySelector('[data-project-tree]');
    const projectTreeToggle = document.querySelector('[data-project-tree-toggle]');
    const projectNodes = document.querySelectorAll('[data-project-node]');
    const openProjectButtons = document.querySelectorAll('[data-open-project]');
    const openTagButtons = document.querySelectorAll('[data-open-tag]');
    const openProjectRenameButtons = document.querySelectorAll('[data-open-project-rename]');
    const openSectionCreateButtons = document.querySelectorAll('[data-open-section-create]');
    const openSectionRenameButtons = document.querySelectorAll('[data-open-section-rename]');
    const openIssueButtons = document.querySelectorAll('#open-issue-modal, [data-open-issue]');
    const projectModal = document.getElementById('project-modal');
    const tagModal = document.getElementById('tag-modal');
    const projectRenameModal = document.getElementById('project-rename-modal');
    const sectionCreateModal = document.getElementById('section-create-modal');
    const sectionRenameModal = document.getElementById('section-rename-modal');
    const issueModal = document.getElementById('issue-modal');
    const projectForm = document.getElementById('project-create-form');
    const tagForm = document.getElementById('tag-create-form');
    const projectRenameForm = document.getElementById('project-rename-form');
    const sectionCreateForm = document.getElementById('section-create-form');
    const sectionRenameForm = document.getElementById('section-rename-form');
    const issueForm = document.getElementById('issue-create-form');
    const projectNameInput = projectForm ? projectForm.querySelector('[name="name"]') : null;
    const tagNameInput = tagForm ? tagForm.querySelector('[name="name"]') : null;
    const projectRenameNameInput = projectRenameForm ? projectRenameForm.querySelector('[name="name"]') : null;
    const projectRenameDescriptionInput = projectRenameForm ? projectRenameForm.querySelector('[name="description"]') : null;
    const projectRenameCodeInput = projectRenameForm ? projectRenameForm.querySelector('[name="code"]') : null;
    const projectRenameIconInput = projectRenameForm ? projectRenameForm.querySelector('[name="icon"]') : null;
    const projectRenameIdInput = projectRenameForm ? projectRenameForm.querySelector('[name="project_id"]') : null;
    const sectionCreateTitleInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="title"]') : null;
    const sectionCreateDescriptionInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="description"]') : null;
    const sectionCreateProjectInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="project_id"]') : null;
    const sectionCreateIconInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="icon"]') : null;
    const sectionRenameTitleInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="title"]') : null;
    const sectionRenameDescriptionInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="description"]') : null;
    const sectionRenameIconInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="icon"]') : null;
    const sectionRenameIdInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="section_id"]') : null;
    const issueTitleInput = issueForm ? issueForm.querySelector('[name="title"]') : null;
    const issueProjectInput = issueForm ? issueForm.querySelector('[name="project_id"]') : null;
    const issueSectionSelect = issueForm ? issueForm.querySelector('[name="section"]') : null;
    const issueProjectPicker = issueForm ? issueForm.querySelector('[data-issue-project-picker]') : null;
    const issueSectionPicker = issueForm ? issueForm.querySelector('[data-issue-section-picker]') : null;
    const issueProjectOptions = issueForm ? Array.from(issueForm.querySelectorAll('[data-project-option]')) : [];
    const issueSectionOptions = issueForm ? Array.from(issueForm.querySelectorAll('[data-section-option]')) : [];
    const issuePickerSearchInputs = issueForm ? Array.from(issueForm.querySelectorAll('[data-picker-search]')) : [];
    const projectSubmitBtn = document.getElementById('project-create-submit');
    const tagSubmitBtn = document.getElementById('tag-create-submit');
    const projectRenameSubmitBtn = document.getElementById('project-rename-submit');
    const sectionCreateSubmitBtn = document.getElementById('section-create-submit');
    const sectionRenameSubmitBtn = document.getElementById('section-rename-submit');
    const issueSubmitBtn = document.getElementById('issue-create-submit');
    const projectIconInput = projectForm ? projectForm.querySelector('[name="icon"]') : null;
    const projectIconPickers = document.querySelectorAll('[data-project-icon-picker]');
    const projectIconGroups = [
        { input: projectIconInput, picker: document.getElementById('project-icon-picker') },
        { input: projectRenameIconInput, picker: document.getElementById('project-rename-icon-picker') },
        { input: sectionCreateIconInput, picker: document.getElementById('section-create-icon-picker') },
        { input: sectionRenameIconInput, picker: document.getElementById('section-rename-icon-picker') }
    ];
    const statusLabels = {
        new: 'Nowe',
        in_progress: 'Realizowane',
        resolved: 'Rozwiązane',
        closed: 'Zamknięte',
        reopened: 'Ponownie otwarte'
    };
    const projectIconSets = [
        {
            label: 'Najczęstsze',
            icon: '⭐',
            items: ['🚀', '⭐', '✅', '⚙️', '💡', '📌', '📋', '📁', '🔧', '🧩', '🎯', '📈', '🔒', '🛠️', '🧪', '🖥️', '📱', '🌐', '☁️', '✨', '🏆', '🎉', '📍', '🔑', '🧰', '🧱', '🪄', '💎', '🧲', '🗓️', '📎', '🔔', '💬', '📣', '🧠', '🧭', '🏁', '🛡️', '🧿', '📌', '📍', '📎', '📔', '📙', '📚', '🗂️', '🗃️', '🧾', '📊', '📉', '📆', '⏰', '⏳', '🔍', '🔎', '🔗', '🔖', '🏷️', '📦', '📫', '📨', '📥', '📤', '📝', '✏️', '🖊️', '🖋️', '🔐', '🔓']
        },
        {
            label: 'Praca',
            icon: '💼',
            items: ['💼', '📊', '📎', '📝', '📅', '⏱️', '🏷️', '📦', '🗂️', '🧾', '✉️', '🔍', '✅', '❗', '📣', '🤝', '👥', '🧠', '🧭', '📔', '📕', '📗', '📘', '📙', '📚', '📓', '📒', '🗃️', '🗄️', '🗒️', '🧑‍💼', '📇', '🗳️', '📤', '📥', '🪪', '🧳', '🏢', '🏦', '📞', '☎️', '📠', '📧', '📨', '📬', '📭', '📮', '🗞️', '📰', '💬', '💭', '🕘', '🕙', '🗓️', '📈', '📉', '💹', '🧮', '💳', '💵', '💶', '💷', '🧾', '⚖️', '📜', '🖋️', '🖇️', '📌']
        },
        {
            label: 'Technologia',
            icon: '💻',
            items: ['💻', '🖥️', '⌨️', '🖱️', '📱', '📲', '🕹️', '💾', '💿', '📀', '🧮', '🔌', '🔋', '🪫', '📡', '🛰️', '🤖', '🧬', '🔬', '⚗️', '🧪', '🧫', '🧲', '⚙️', '🛠️', '🔧', '🔩', '⛓️', '🧰', '🪛', '🧑‍💻', '🖨️', '📟', '📠', '🗜️', '🧯', '🛜', '💽', '💡', '🔐', '🔒', '🔓', '🔑', '🗝️', '📶', '📳', '📴', '🔊', '🔉', '🔈', '🎛️', '🎚️', '📺', '📷', '📹', '🎥', '🔍', '🧭', '🧱', '🧩', '🪄', '🧬', '🩻', '💫', '✨', '⚡', '🔥', '🌐', '☁️']
        },
        {
            label: 'Kreatywne',
            icon: '🎨',
            items: ['🎨', '🖌️', '🖍️', '✏️', '✒️', '🖊️', '🖋️', '📐', '📏', '✂️', '🧵', '🪡', '🎭', '🎬', '🎧', '🎤', '🎹', '🥁', '🎸', '🎻', '🎲', '🧩', '🪄', '📷', '📸', '🎥', '📹', '🖼️', '🌈', '💫', '🪩', '🎼', '🎵', '🎶', '🎙️', '🎚️', '🎛️', '🪅', '🪆', '🧶', '🖋️', '🖊️', '📝', '📜', '📄', '📃', '📑', '🗒️', '🖇️', '📌', '📍', '🔖', '✨', '🌟', '⭐', '🔥', '💥', '💡', '🎞️', '📽️', '🎟️', '🎫', '🎪', '🕹️', '🎯', '🎳', '🧸', '🪀', '🪁']
        },
        {
            label: 'Status',
            icon: '⚡',
            items: ['⚡', '🔥', '⭐', '🔔', '🟢', '🟡', '🔴', '🔵', '🟣', '🟠', '⬆️', '⬇️', '➡️', '🔁', '⏳', '🚧', '🧯', '🛡️', '🏁', '🎉', '💥', '💢', '💤', '💯', '🔜', '🔝', '🆕', '🆒', '🆗', '📛', '🚨', '✅', '☑️', '❌', '❗', '❓', '♻️', '🔄', '⛔', '💬', '⭕', '🚫', '❎', '✔️', '➕', '➖', '➗', '✳️', '✴️', '🔆', '🔅', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚪', '⚫', '🟤', '🔺', '🔻', '🔸', '🔹', '🔶', '🔷', '💠', '🔰']
        },
        {
            label: 'Zespół',
            icon: '🙂',
            items: ['🙂', '😀', '😎', '🤓', '🧐', '🤩', '🥳', '🙌', '👏', '👍', '💪', '🙏', '👋', '🤝', '👥', '🧑', '👩', '👨', '🧑‍💻', '👩‍💻', '👨‍💻', '🧑‍🎨', '👩‍🔧', '👨‍🔧', '🧑‍🚀', '👩‍🏫', '👨‍🏫', '🧑‍💼', '👩‍💼', '👨‍💼', '😁', '😄', '😃', '😊', '😉', '😌', '😍', '😇', '😋', '😜', '🤠', '😺', '👌', '✌️', '🤞', '🤟', '🤘', '👊', '✊', '🫶', '🤲', '💁', '🙋', '🙆', '🙅', '🧑‍🏫', '🧑‍🔧', '🧑‍🔬', '🧑‍🚒', '🧑‍✈️', '🧑‍⚕️', '🧑‍⚖️', '🧑‍🌾']
        },
        {
            label: 'Plan',
            icon: '🗓️',
            items: ['🗓️', '📅', '📆', '⏰', '⏱️', '⏲️', '⌛', '⏳', '🕒', '📍', '🧭', '🗺️', '🧱', '🏗️', '🛤️', '🚦', '🧾', '📋', '📝', '✍️', '📌', '📎', '🔖', '🏷️', '🎯', '🏁', '🧮', '📊', '📈', '📉', '🕐', '🕑', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚', '🕛', '📖', '📚', '🗒️', '🗂️', '🗃️', '📦', '🚧', '🔁', '🔄', '➡️', '⬅️', '⬆️', '⬇️', '🔜', '🔝', '✅', '☑️', '⚠️', '🚩']
        },
        {
            label: 'Biznes',
            icon: '💰',
            items: ['💰', '💵', '💶', '💷', '💳', '🧾', '🏦', '🏢', '🏬', '🏭', '🏗️', '🚚', '📦', '📫', '📮', '📤', '📥', '📨', '📧', '📞', '☎️', '📠', '🪪', '🧳', '🛒', '🧺', '🤝', '📊', '📈', '📉', '💸', '💎', '⚖️', '🧮', '📝', '🗂️', '📋', '📌', '🔐', '🔑', '📇', '🗃️', '🗄️', '🏷️', '📣', '📰', '🗞️', '📢', '🎯', '🏁', '🧭', '🚀', '⭐', '🏆', '✅', '📅', '⏱️', '🌐', '☁️', '🔗']
        },
        {
            label: 'Miejsca',
            icon: '🌍',
            items: ['🌍', '🌎', '🌏', '🗺️', '🏙️', '🌆', '🌃', '🏢', '🏫', '🏛️', '🏥', '🏦', '🏭', '🏗️', '⛲', '🌉', '🚉', '✈️', '🚀', '🛸', '🚗', '🚕', '🚲', '🛴', '🚢', '⚓', '🏝️', '🏕️', '🏖️', '🏜️', '🏞️', '⛰️', '🏔️', '🌋', '🗻', '🏟️', '🏰', '🗼', '🗽', '⛪', '🕌', '🛕', '🕍', '⛩️', '🕋', '⛲', '⛺', '🚏', '🚦', '🛤️', '🛣️', '🚇', '🚆', '🚊', '🚍', '🚐', '🛵']
        },
        {
            label: 'Natura',
            icon: '🌿',
            items: ['🌿', '🌱', '🌳', '🌲', '🍀', '🌵', '🌾', '🌻', '🌼', '🌸', '🌺', '🍄', '🌞', '🌙', '⭐', '🌟', '☁️', '⛅', '🌧️', '⛈️', '❄️', '💧', '🌊', '🔥', '💎', '🪨', '⛰️', '🏔️', '🌋', '🏕️', '🌷', '🪷', '💐', '🌹', '🥀', '🪻', '🌴', '🪵', '🍁', '🍂', '🍃', '🪹', '🪺', '🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘', '🌈', '☀️', '🌤️', '🌦️', '🌩️', '🌨️', '🌬️', '🫧', '💦', '🧊']
        },
        {
            label: 'Jedzenie',
            icon: '🍕',
            items: ['🍕', '🍔', '🌭', '🥪', '🌮', '🌯', '🥗', '🍱', '🍜', '🍝', '🍣', '🍩', '🍪', '🍰', '🧁', '🍫', '🍿', '☕', '🍵', '🥤', '🧃', '🍎', '🍋', '🍓', '🍇', '🍉', '🥑', '🥕', '🌽', '🧀', '🥐', '🥨', '🥞', '🧇', '🥯', '🍞', '🥘', '🥫', '🍯', '🫖', '🍏', '🍐', '🍊', '🍌', '🍍', '🥭', '🍑', '🍒', '🫐', '🥝', '🍅', '🫒', '🥥', '🥦', '🥬', '🥒', '🌶️', '🫑', '🥔', '🍠', '🥜', '🫘', '🍄', '🥚', '🧈', '🥖', '🥩', '🍗', '🍖', '🍤', '🍚']
        },
        {
            label: 'Edukacja',
            icon: '🎓',
            items: ['🎓', '📚', '📖', '📕', '📗', '📘', '📙', '📓', '📒', '📝', '✏️', '🖊️', '🧮', '📐', '📏', '🔬', '🧪', '🧬', '🧫', '🌍', '🗺️', '🧠', '💡', '🏫', '👩‍🏫', '👨‍🏫', '🧑‍🏫', '🎒', '🔖', '🏅', '📔', '📒', '📄', '📃', '📑', '📊', '📈', '📉', '🗒️', '🗂️', '🖍️', '🖌️', '🖋️', '🔎', '🔍', '🧭', '⚗️', '🔭', '🪐', '🌐', '💬', '🗣️', '🎯', '🏆', '⭐', '✅', '☑️', '🧩', '🪄', '⏱️']
        },
        {
            label: 'Sport',
            icon: '🏅',
            items: ['🏅', '🏆', '🥇', '🥈', '🥉', '⚽', '🏀', '🏈', '⚾', '🎾', '🏐', '🏉', '🥏', '🎱', '🏓', '🏸', '🥊', '🥋', '⛳', '🏹', '🎣', '⛸️', '🎿', '🏂', '🏋️', '🚴', '🏃', '🏊', '🧗', '🤸', '🏌️', '🤾', '⛹️', '🤼', '🤽', '🚣', '🏄', '🛶', '🥌', '🛷', '🛼', '🛹', '🎽', '🥅', '🥎', '🏏', '🏑', '🥍', '🪃', '🎯', '🏟️', '🎟️', '📣', '🔥', '⚡', '💪', '👏', '🙌', '🏁', '🚩']
        },
        {
            label: 'Zdrowie',
            icon: '💚',
            items: ['💚', '❤️', '🩺', '💊', '🩹', '🩻', '🧬', '🧪', '🔬', '🧫', '🏥', '🚑', '🧘', '🥗', '🍎', '🥑', '💧', '🌿', '🌞', '🛌', '⏰', '🧠', '💪', '🫶', '😌', '🙂', '🌱', '🍵', '🫧', '✨', '🫀', '🫁', '🦷', '🦴', '👁️', '👂', '👃', '🧴', '🧼', '🪥', '🛁', '🚿', '🧊', '🥦', '🥬', '🥕', '🍋', '🍓', '🫐', '🥤', '🧃', '☀️', '🌈', '🌙', '⭐', '✅', '📋', '📅', '⏱️', '🔔']
        },
        {
            label: 'Symbole',
            icon: '🔣',
            items: ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '☮️', '☯️', '♻️', '✅', '☑️', '✔️', '❌', '❎', '➕', '➖', '➗', '✳️', '🔆', '🔅', '🔱', '⚜️', '🔰', '⭕', '❇️', '✴️', '💠', '🔶', '🔷', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚫', '⚪', '🟤', '⬛', '⬜', '◼️', '◻️', '◾', '◽', '▪️', '▫️', '🔺', '🔻', '🔸', '🔹', '🔘', '🔳', '🔲', '➰', '➿', '〽️', '⚠️', '🚫']
        }
    ];
    const projectIconSetExtras = {
        'Najczęstsze': ['📁', '📂', '🗂️', '🗄️', '🗃️', '📇', '🧾', '🧮', '📜', '📄', '📃', '📑', '📒', '🗒️', '🖇️', '🧷', '🪧', '📡', '📶', '🛜', '🔋', '🔌', '💾', '💽', '🖨️', '🧑‍💻', '🧑‍🎨', '🧑‍💼', '🧑‍🔧', '🧑‍🏫', '🧑‍🔬', '💪', '🙌', '👏', '🤝', '🫶', '🚩', '⚠️', '🚨', '⛔', '⭕', '🔰', '💠', '🔶', '🔷', '🟢', '🟡', '🔴', '🟣'],
        'Praca': ['📁', '📂', '🗂️', '🗄️', '📑', '📄', '📃', '🧷', '🖊️', '✒️', '🖌️', '🔖', '🔗', '📍', '📆', '🕒', '⏳', '⌛', '🔔', '🚩', '⚠️', '🚨', '⛔', '☑️', '✔️', '❌', '🔄', '♻️', '🔎', '🔒', '🔓', '🗝️', '🏛️', '🏭', '🏗️', '🚛', '🚢', '✈️', '📦', '🧰', '🛠️', '⚙️', '💡', '🎯', '💯', '🏆', '🥇', '⭐'],
        'Technologia': ['🧑‍🔬', '🧑‍🚀', '🧑‍🔧', '🧑‍🏭', '📁', '📂', '🗂️', '🗄️', '📊', '📈', '📉', '🧾', '📋', '🖇️', '🧷', '📎', '🔖', '🏷️', '🧱', '🧰', '🪚', '🪜', '🧯', '🛡️', '🧿', '🚨', '⚠️', '✅', '☑️', '❌', '⭕', '♻️', '🔄', '🔁', '🔀', '🔂', '🔃', '⬆️', '⬇️', '➡️', '⬅️', '↗️', '↘️', '↪️', '↩️', '⏫', '⏬'],
        'Kreatywne': ['🖼️', '🪞', '🧿', '🎇', '🎆', '🌠', '🌌', '🌃', '🌆', '🌅', '🌄', '☀️', '🌙', '🌕', '🌻', '🌸', '🌺', '🌼', '🪷', '💐', '💎', '🔮', '🕯️', '🎁', '🎀', '🎊', '🎉', '🪄', '🧵', '🪡', '🧶', '🧷', '🖇️', '📎', '📚', '📖', '📕', '📗', '📘', '📙', '🧠', '💭', '💬', '🗯️', '💥', '💫', '🫧'],
        'Status': ['🟩', '🟨', '🟥', '🟦', '🟪', '🟧', '🟫', '⬛', '⬜', '◼️', '◻️', '◾', '◽', '▪️', '▫️', '🔳', '🔲', '🔘', '🔵', '🔴', '🟢', '🟡', '🟣', '🟠', '⚫', '⚪', '🟤', '🚩', '🏳️', '🏁', '📍', '📌', '🔔', '📣', '📢', '💡', '💥', '✨', '🌟', '⭐', '💯', '🔝', '🆙', '🆗', '🆕', '🆓', '🆘', '🛑'],
        'Zespół': ['😆', '🤣', '😂', '🥰', '😘', '😗', '😙', '😚', '🤗', '🤭', '🤫', '🤔', '🫡', '🤨', '😐', '😑', '😶', '🫥', '😶‍🌫️', '🙄', '😬', '😮‍💨', '🤥', '😴', '😪', '😮', '😲', '🥱', '😤', '😮‍💨', '👋', '🤚', '🖐️', '✋', '🖖', '🫱', '🫲', '🫳', '🫴', '👈', '👉', '👆', '👇', '☝️', '🫵', '🧑‍🍳', '🧑‍🎤', '🧑‍🚒'],
        'Plan': ['📌', '📍', '🧷', '🖇️', '📎', '🔖', '🏷️', '📁', '📂', '🗄️', '🗃️', '📇', '📜', '📄', '📃', '📑', '📔', '📕', '📗', '📘', '📙', '📓', '📒', '🧾', '🧮', '🔍', '🔎', '🔔', '📣', '📢', '🚨', '⛔', '⭕', '❌', '✔️', '➕', '➖', '✳️', '🔆', '🔅', '🟢', '🟡', '🔴', '🔵', '🟣', '🟠', '💯', '🎉'],
        'Biznes': ['📁', '📂', '📑', '📄', '📃', '📜', '📔', '📕', '📗', '📘', '📙', '📓', '🗒️', '🧷', '🖇️', '📎', '🔖', '🔗', '🗝️', '🔒', '🔓', '🏛️', '🏫', '🏟️', '🏪', '🏬', '🏢', '🏭', '🏗️', '🚛', '🚚', '🚢', '✈️', '🚀', '📦', '🛒', '🧺', '💡', '⚙️', '🛠️', '🧰', '📡', '📶', '🛜', '🎖️', '🏅', '🥇'],
        'Miejsca': ['🏯', '🏚️', '🏙️', '🌁', '🌄', '🌅', '🌇', '🌉', '🎠', '🛝', '🎡', '🎢', '⛱️', '🏨', '🏩', '🏪', '🏬', '🏤', '🏣', '🏦', '🏫', '🏢', '🏭', '🏗️', '🚲', '🛴', '🛵', '🏍️', '🚙', '🚎', '🚒', '🚑', '🚓', '🚕', '🚗', '🚚', '🚛', '🚜', '🚁', '🛩️', '🛫', '🛬', '🚤', '⛵', '🛳️', '🚢', '🧭', '📍'],
        'Natura': ['🌰', '🫚', '🪸', '🪨', '🪵', '🍇', '🍈', '🍉', '🍊', '🍋', '🍌', '🍍', '🥭', '🍎', '🍏', '🍐', '🍑', '🍒', '🍓', '🫐', '🥝', '🍅', '🫒', '🥥', '🥑', '🥦', '🥬', '🥒', '🌶️', '🫑', '🌽', '🥕', '🧄', '🧅', '🥔', '🍠', '🫘', '🥜', '🌍', '🌎', '🌏', '🪐', '☄️', '💫', '⚡', '🔥', '🧊', '💧'],
        'Jedzenie': ['🍛', '🍲', '🫕', '🥣', '🥡', '🥟', '🥠', '🥮', '🍢', '🍡', '🍧', '🍨', '🍦', '🥧', '🍮', '🍭', '🍬', '🍯', '🍼', '🥛', '🫗', '🍶', '🍾', '🍷', '🍸', '🍹', '🍺', '🍻', '🥂', '🥃', '🧉', '🧋', '🧊', '🥄', '🍴', '🍽️', '🥢', '🧂', '🔪', '🏺', '🛒', '🧺', '📦', '🎂', '🍥', '🍘', '🍙', '🍞'],
        'Edukacja': ['🏫', '🏛️', '🧑‍🎓', '🧑‍🏫', '🧑‍🔬', '🧑‍💻', '🧑‍🎨', '🧑‍⚖️', '🧑‍🚀', '🧑‍🔧', '🧑‍⚕️', '🧑‍💼', '📌', '📍', '📎', '🧷', '🖇️', '🔖', '🏷️', '📁', '📂', '🗄️', '🗃️', '📇', '🧾', '📜', '📰', '🗞️', '💡', '🔦', '🕯️', '🔮', '🪄', '🧿', '🎓', '🏅', '🥇', '🎖️', '🎯', '🧩', '🧱', '⚙️', '🛠️', '🔧', '📡', '🌐', '☁️', '🛜'],
        'Sport': ['🥅', '🏟️', '🎖️', '🎗️', '🎫', '🎟️', '🎪', '🎯', '🎲', '🎳', '🕹️', '🪀', '🪁', '🥁', '📣', '📢', '🔔', '🚩', '🏁', '✅', '☑️', '⭐', '🌟', '💫', '✨', '💥', '💯', '🔥', '⚡', '💪', '🦾', '🧘', '⏱️', '⏲️', '⌛', '⏳', '📊', '📈', '🏔️', '⛰️', '🏕️', '🏖️', '🌊', '☀️', '❄️', '🧊', '🎿', '🛷'],
        'Zdrowie': ['🧑‍⚕️', '👩‍⚕️', '👨‍⚕️', '🧑‍🔬', '👩‍🔬', '👨‍🔬', '🧘‍♀️', '🧘‍♂️', '🏃', '🚶', '🏋️', '🤸', '🤽', '🏊', '🚴', '🛌', '🧎', '🧍', '🍵', '🫖', '🥛', '🍼', '🧂', '🥣', '🥗', '🍯', '🍊', '🍌', '🍇', '🍉', '🥝', '🍅', '🫒', '🥥', '🥒', '🌽', '🫘', '🥜', '💚', '💙', '🤍', '💛', '🩵', '✨', '🌟', '💫', '🔆', '🔅'],
        'Dom': ['🏚️', '🏗️', '🧱', '🪵', '🪨', '🪜', '🪚', '🔨', '⛏️', '⚒️', '🛠️', '🗜️', '⛓️', '🧲', '🔌', '🔋', '🪫', '📦', '🧺', '🛒', '🛍️', '🎁', '🪑', '🛋️', '🛏️', '🚪', '🧯', '🔒', '🔓', '🗝️', '🕯️', '💡', '🔦', '📺', '📻', '🎛️', '🎚️', '🎵', '🎶', '📚', '📖', '🧸', '🧶', '🪡', '🌷', '🌼', '🌸', '🌱'],
        'Symbole': ['🟩', '🟨', '🟥', '🟦', '🟪', '🟧', '🟫', '🔶', '🔷', '🔸', '🔹', '💠', '🔘', '🔳', '🔲', '🔺', '🔻', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫', '⚪', '❔', '❕', '❓', '❗', '‼️', '⁉️', '〰️', '➰', '➿', '🔱', '⚜️', '🔰', '♻️', '✅', '☑️', '✔️', '✖️', '❌', '⭕', '🚫', '⛔', '🛑']
    };
    projectIconSets.forEach(set => {
        set.items = [...new Set([...set.items, ...(projectIconSetExtras[set.label] || [])])];
    });
    const projectIconSetKeywords = {
        'Najczęstsze': ['popularne', 'ulubione', 'gwiazda', 'start', 'zadanie', 'projekt'],
        'Praca': ['firma', 'biuro', 'biznes', 'dokument', 'mail', 'spotkanie', 'zespół', 'zespol'],
        'Technologia': ['tech', 'komputer', 'laptop', 'telefon', 'kod', 'programowanie', 'narzędzia', 'narzedzia'],
        'Kreatywne': ['design', 'projektowanie', 'sztuka', 'muzyka', 'foto', 'kamera', 'pomysł', 'pomysl'],
        'Status': ['priorytet', 'ważne', 'wazne', 'gotowe', 'błąd', 'blad', 'alert', 'kolor'],
        'Zespół': ['ludzie', 'osoba', 'uśmiech', 'usmiech', 'team', 'człowiek', 'czlowiek'],
        'Plan': ['kalendarz', 'czas', 'termin', 'harmonogram', 'mapa', 'cel'],
        'Biznes': ['pieniądze', 'pieniadze', 'finanse', 'bank', 'sprzedaż', 'sprzedaz', 'sklep'],
        'Miejsca': ['miasto', 'budynek', 'podróż', 'podroz', 'transport', 'auto', 'samolot'],
        'Natura': ['roślina', 'roslina', 'drzewo', 'kwiat', 'pogoda', 'woda', 'ogień', 'ogien'],
        'Jedzenie': ['food', 'pizza', 'kawa', 'napój', 'napoj', 'owoc', 'warzywo'],
        'Edukacja': ['szkoła', 'szkola', 'nauka', 'książka', 'ksiazka', 'student', 'uczeń', 'uczen'],
        'Sport': ['gra', 'mecz', 'medal', 'puchar', 'piłka', 'pilka', 'trening'],
        'Zdrowie': ['medycyna', 'lekarz', 'serce', 'apteczka', 'ćwiczenia', 'cwiczenia'],
        'Symbole': ['znak', 'serce', 'kolor', 'checkbox', 'plus', 'minus', 'okrąg', 'okrag']
    };
    const projectIconKeywords = {
        '🚀': ['rakieta', 'start', 'launch'],
        '⭐': ['gwiazda', 'ulubione', 'star'],
        '✅': ['check', 'gotowe', 'zrobione', 'ok'],
        '⚙️': ['ustawienia', 'trybik', 'settings'],
        '💡': ['pomysł', 'pomysl', 'idea'],
        '📌': ['pinezka', 'przypięte', 'przypiete'],
        '📋': ['lista', 'clipboard'],
        '📁': ['folder', 'projekt'],
        '🔧': ['klucz', 'naprawa', 'narzędzie', 'narzedzie'],
        '🧩': ['puzzle', 'część', 'czesc'],
        '🎯': ['cel', 'target'],
        '📈': ['wzrost', 'wykres'],
        '🔒': ['blokada', 'zamknięte', 'zamkniete'],
        '🖥️': ['monitor', 'komputer'],
        '📱': ['telefon', 'mobile'],
        '🌐': ['internet', 'web', 'sieć', 'siec'],
        '☁️': ['chmura', 'cloud'],
        '💼': ['praca', 'teczka', 'biuro'],
        '💻': ['laptop', 'komputer', 'kod'],
        '🎨': ['sztuka', 'design', 'kolor'],
        '🙂': ['uśmiech', 'usmiech', 'osoba'],
        '🗓️': ['kalendarz', 'plan', 'termin'],
        '💰': ['pieniądze', 'pieniadze', 'finanse'],
        '🌍': ['świat', 'swiat', 'ziemia'],
        '🌿': ['natura', 'liść', 'lisc'],
        '🍕': ['pizza', 'jedzenie'],
        '🎓': ['edukacja', 'nauka'],
        '🏅': ['medal', 'sport'],
        '💚': ['zdrowie', 'serce'],
        '🔣': ['symbole', 'znaki'],
        '📅': ['data', 'kalendarz'],
        '⏰': ['alarm', 'czas'],
        '🔍': ['szukaj', 'lupa'],
        '📦': ['paczka', 'box'],
        '📝': ['notatka', 'pisanie'],
        '🏢': ['firma', 'budynek'],
        '📞': ['telefon', 'kontakt'],
        '🤝': ['współpraca', 'wspolpraca'],
        '👥': ['zespół', 'zespol', 'ludzie'],
        '🎬': ['film', 'video'],
        '🎧': ['audio', 'muzyka'],
        '📷': ['aparat', 'foto'],
        '🔥': ['ogień', 'ogien', 'pilne'],
        '🔔': ['dzwonek', 'powiadomienie'],
        '❌': ['anuluj', 'błąd', 'blad'],
        '⚠️': ['uwaga', 'ostrzeżenie', 'ostrzezenie'],
        '🏠': ['dom', 'home'],
        '❤️': ['serce', 'miłość', 'milosc']
    };
    const normalizedProjectIconSearch = projectIconSets.map(set => ({
        label: set.label,
        items: set.items.map(icon => ({
            icon,
            keywords: [
                set.label,
                ...(projectIconSetKeywords[set.label] || []),
                ...(projectIconKeywords[icon] || [])
            ].join(' ').toLowerCase()
        }))
    }));
    let activeIconPicker = null;
    let activeIconInput = null;
    let emojiPicker = null;
    let emojiPickerSearch = null;
    let emojiPickerBody = null;
    let activeIconSetIndex = 0;

    function updateProjectSubmitState() {
        if (!projectSubmitBtn || !projectNameInput) return;
        projectSubmitBtn.disabled = projectNameInput.value.trim().length === 0;
    }

    function updateTagSubmitState() {
        if (!tagSubmitBtn || !tagNameInput) return;
        tagSubmitBtn.disabled = tagNameInput.value.trim().length === 0;
    }

    function updateIssueSubmitState() {
        if (!issueSubmitBtn || !issueTitleInput) return;
        issueSubmitBtn.disabled = issueTitleInput.value.trim().length === 0;
    }

    function updateProjectRenameSubmitState() {
        if (!projectRenameSubmitBtn || !projectRenameNameInput) return;
        projectRenameSubmitBtn.disabled = projectRenameNameInput.value.trim().length === 0;
    }

    function updateSectionCreateSubmitState() {
        if (!sectionCreateSubmitBtn || !sectionCreateTitleInput) return;
        sectionCreateSubmitBtn.disabled = sectionCreateTitleInput.value.trim().length === 0;
    }

    function updateSectionRenameSubmitState() {
        if (!sectionRenameSubmitBtn || !sectionRenameTitleInput) return;
        sectionRenameSubmitBtn.disabled = sectionRenameTitleInput.value.trim().length === 0;
    }

    function closeCreateMenu() {
        if (!createMenu || !createMenuToggle) return;
        createMenu.classList.remove('is-open');
        createMenuToggle.setAttribute('aria-expanded', 'false');
    }

    function closeProjectActionMenus(exceptMenu = null) {
        projectActionMenus.forEach(menu => {
            if (menu === exceptMenu) return;
            menu.classList.remove('is-open');
            menu.querySelector('[data-project-menu-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    function closeSectionActionMenu() {
        if (!sectionActionMenu) return;
        sectionActionMenu.classList.remove('is-open');
        sectionActionMenu.querySelector('[data-section-menu-toggle]')?.setAttribute('aria-expanded', 'false');
    }

    function closeStatusFilterMenu() {
        if (!statusFilterMenu || !statusFilterToggle) return;
        statusFilterMenu.classList.remove('is-open');
        statusFilterToggle.setAttribute('aria-expanded', 'false');
    }

    function closePriorityFilterMenu() {
        if (!priorityFilterMenu || !priorityFilterToggle) return;
        priorityFilterMenu.classList.remove('is-open');
        priorityFilterToggle.setAttribute('aria-expanded', 'false');
    }

    function getPriorityFilterIconMarkup(priority) {
        if (!priority) return '';
        if (priority === 'urgent') {
            return '<span class="tasks-row-priority priority-urgent"><span class="tasks-priority-icon"><span class="tasks-priority-urgent-mark">!</span></span></span>';
        }
        if (priority === 'none') {
            return '<span class="tasks-row-priority priority-none"><span class="tasks-priority-icon"><span class="tasks-priority-no-mark"></span></span></span>';
        }
        return `<span class="tasks-row-priority priority-${priority}"><span class="tasks-priority-icon"><span class="tasks-priority-bars"><span></span><span></span><span></span></span></span></span>`;
    }

    function getFilterButtonText(button) {
        if (!button) return '';
        const clone = button.cloneNode(true);
        clone.querySelectorAll('[aria-hidden="true"]').forEach(node => node.remove());
        return clone.textContent.trim();
    }

    function closeIssuePickers(exceptPicker = null) {
        [issueProjectPicker, issueSectionPicker].forEach(picker => {
            if (!picker || picker === exceptPicker) return;
            picker.classList.remove('is-open');
            picker.querySelector('[data-picker-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    function normalizePickerSearch(value) {
        return (value || '').trim().toLowerCase();
    }

    function filterPickerSearch(input) {
        const query = normalizePickerSearch(input?.value);
        const type = input?.dataset.pickerSearchType || '';
        const selectedProjectId = issueProjectInput?.value || '';

        if (type === 'project') {
            issueProjectOptions.forEach(option => {
                const text = normalizePickerSearch(option.dataset.projectName || option.textContent);
                option.hidden = query ? !text.includes(query) : false;
            });
            return;
        }

        if (type === 'section') {
            issueSectionOptions.forEach(option => {
                const belongsToProject = !selectedProjectId || option.dataset.sectionProjectId === selectedProjectId;
                const text = normalizePickerSearch(option.dataset.sectionTitle || option.textContent);
                option.hidden = !belongsToProject || (query ? !text.includes(query) : false);
            });
        }
    }

    function resetPickerSearch(picker) {
        const input = picker?.querySelector('[data-picker-search]');
        if (!input) return;
        input.value = '';
        filterPickerSearch(input);
    }

    function getCollapsedProjects() {
        try {
            return new Set(JSON.parse(localStorage.getItem('collapsedTaskProjects') || '[]'));
        } catch (error) {
            return new Set();
        }
    }

    function saveCollapsedProjects(collapsedProjects) {
        try {
            localStorage.setItem('collapsedTaskProjects', JSON.stringify([...collapsedProjects]));
        } catch (error) {
            // Ignore storage failures; the in-page collapse state still works.
        }
    }

    function getProjectTreeCollapsed() {
        try {
            return localStorage.getItem('collapsedTaskProjectTree') === 'true';
        } catch (error) {
            return false;
        }
    }

    function saveProjectTreeCollapsed(isCollapsed) {
        try {
            localStorage.setItem('collapsedTaskProjectTree', String(isCollapsed));
        } catch (error) {
            // Ignore storage failures; the in-page collapse state still works.
        }
    }

    function setProjectTreeCollapsed(isCollapsed) {
        if (!projectTree || !projectTreeToggle) return;

        projectTree.classList.toggle('is-collapsed', isCollapsed);
        projectTreeToggle.setAttribute('aria-expanded', String(!isCollapsed));
        projectTreeToggle.setAttribute('aria-label', `${isCollapsed ? 'Rozwiń' : 'Zwiń'} Moje projekty`);
    }

    function setProjectCollapsed(projectNode, isCollapsed) {
        const toggle = projectNode.querySelector('[data-project-collapse-toggle]');
        const projectName = projectNode.querySelector('.tasks-project-title span:not(.tasks-project-badge)')?.textContent?.trim() || 'projekt';

        projectNode.classList.toggle('is-collapsed', isCollapsed);
        toggle?.setAttribute('aria-expanded', String(!isCollapsed));
        toggle?.setAttribute('aria-label', `${isCollapsed ? 'Rozwiń' : 'Zwiń'} projekt ${projectName}`);
    }

    function clearProjectTreeInitialState() {
        document.documentElement.classList.remove('tasks-project-tree-initially-collapsed');
        document.getElementById('tasks-project-tree-initial-state')?.remove();
    }

    function openModal(modal, focusTarget, onOpen) {
        if (!modal) return;
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
        closeCreateMenu();
        if (onOpen) onOpen();
        setTimeout(() => focusTarget?.focus(), 50);
    }

    function closeModal(modal) {
        if (!modal) return;
        closeEmojiPicker();
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        if (!document.querySelector('.tasks-modal.is-open')) {
            document.body.classList.remove('modal-open');
        }
    }

    function createSectionDefaultIconSvg() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'tasks-section-default-icon');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('aria-hidden', 'true');

        ['M21 5.5 10 16.5 4.5 11', 'M20 12v6.5A2.5 2.5 0 0 1 17.5 21h-12A2.5 2.5 0 0 1 3 18.5v-12A2.5 2.5 0 0 1 5.5 4H15'].forEach(d => {
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', d);
            svg.appendChild(path);
        });

        return svg;
    }

    function createEmptyIconSvg() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'tasks-empty-icon');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('aria-hidden', 'true');

        ['M5 5l14 14', 'M19 5 5 19'].forEach(d => {
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', d);
            svg.appendChild(path);
        });

        return svg;
    }

    function renderProjectIcon(display, icon) {
        if (!display) return;
        display.textContent = '';
        if (!icon) {
            display.appendChild(createEmptyIconSvg());
            return;
        }
        if (icon === 'check' || icon === '✅') {
            display.appendChild(createSectionDefaultIconSvg());
            return;
        }
        display.textContent = icon;
    }

    function setIconValue(input, picker, icon) {
        const normalizedIcon = (icon || '').trim();
        if (input) input.value = normalizedIcon;
        const display = picker ? picker.querySelector('[data-selected-project-icon]') : null;
        renderProjectIcon(display, normalizedIcon);
    }

    function setIssueChip(picker, label, icon, color) {
        if (!picker) return;
        const labelEl = picker.querySelector('[data-picker-label]');
        const iconEl = picker.querySelector('[data-picker-icon]');
        const toggle = picker.querySelector('[data-picker-toggle]');

        if (labelEl) labelEl.textContent = label || '';
        if (iconEl) iconEl.textContent = icon || '';
        if (toggle && color) toggle.style.setProperty('--project-icon-fg', color);
    }

    function getSelectedSectionOption() {
        if (!issueSectionSelect?.value) return null;
        return issueSectionOptions.find(option => option.dataset.sectionId === issueSectionSelect.value) || null;
    }

    function selectIssueSection(sectionId) {
        const sectionOption = issueSectionOptions.find(option => option.dataset.sectionId === String(sectionId));
        if (!sectionOption || !issueSectionSelect) return false;

        issueSectionSelect.value = sectionOption.dataset.sectionId || '';
        setIssueChip(issueSectionPicker, sectionOption.dataset.sectionTitle || 'Wybierz grupę', sectionOption.dataset.sectionIcon || '');
        return true;
    }

    function filterIssueSections(projectId) {
        let firstVisibleSectionId = '';
        const sectionSearch = issueSectionPicker?.querySelector('[data-picker-search]');
        const query = normalizePickerSearch(sectionSearch?.value);

        issueSectionOptions.forEach(option => {
            const text = normalizePickerSearch(option.dataset.sectionTitle || option.textContent);
            const isVisible = (!projectId || option.dataset.sectionProjectId === String(projectId)) && (!query || text.includes(query));
            option.hidden = !isVisible;
            if (isVisible && !firstVisibleSectionId) {
                firstVisibleSectionId = option.dataset.sectionId || '';
            }
        });

        return firstVisibleSectionId;
    }

    function selectIssueProject(projectId, preferredSectionId = '') {
        const projectOption = issueProjectOptions.find(option => option.dataset.projectId === String(projectId)) || issueProjectOptions[0];
        if (!projectOption) return;

        const selectedProjectId = projectOption.dataset.projectId || '';
        if (issueProjectInput) issueProjectInput.value = selectedProjectId;
        setIssueChip(
            issueProjectPicker,
            projectOption.dataset.projectName || 'Wybierz projekt',
            projectOption.dataset.projectIcon || '',
            projectOption.dataset.projectColor || ''
        );

        const firstVisibleSectionId = filterIssueSections(selectedProjectId);
        const currentSectionOption = getSelectedSectionOption();
        const currentSectionFits = currentSectionOption?.dataset.sectionProjectId === selectedProjectId;
        const nextSectionId = preferredSectionId || (currentSectionFits ? currentSectionOption.dataset.sectionId : '') || projectOption.dataset.defaultSectionId || firstVisibleSectionId;

        if (!selectIssueSection(nextSectionId) && firstVisibleSectionId) {
            selectIssueSection(firstVisibleSectionId);
        }
    }

    function syncIssuePickers() {
        if (!issueForm || !issueProjectOptions.length) return;

        const selectedSectionOption = getSelectedSectionOption();
        const projectId = issueProjectInput?.value || selectedSectionOption?.dataset.sectionProjectId || issueProjectOptions[0]?.dataset.projectId || '';
        selectIssueProject(projectId, selectedSectionOption?.dataset.sectionId || '');
    }

    function syncProjectIconPickers() {
        projectIconGroups.forEach(group => {
            if (!group.input || !group.picker) return;
            setIconValue(group.input, group.picker, group.input.value);
        });
    }

    function getPickerForInput(input) {
        const group = projectIconGroups.find(item => item.input === input);
        return group ? group.picker : null;
    }

    function createEmojiPicker() {
        if (emojiPicker) return emojiPicker;

        emojiPicker = document.createElement('div');
        emojiPicker.className = 'tasks-emoji-picker';
        emojiPicker.setAttribute('role', 'dialog');
        emojiPicker.setAttribute('aria-label', 'Wybór ikony projektu');

        const tabs = document.createElement('div');
        tabs.className = 'tasks-emoji-picker__tabs';
        projectIconSets.forEach((set, index) => {
            const tab = document.createElement('button');
            tab.type = 'button';
            tab.textContent = set.icon;
            tab.title = set.label;
            tab.setAttribute('aria-label', set.label);
            tab.addEventListener('click', () => {
                activeIconSetIndex = index;
                emojiPickerSearch.value = '';
                renderEmojiPicker();
            });
            tabs.appendChild(tab);
        });

        const searchWrap = document.createElement('div');
        searchWrap.className = 'tasks-emoji-picker__search';
        searchWrap.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="M16.5 16.5L21 21"></path></svg>';

        emojiPickerSearch = document.createElement('input');
        emojiPickerSearch.type = 'search';
        emojiPickerSearch.placeholder = 'Szukaj lub wpisz ikonę';
        emojiPickerSearch.setAttribute('aria-label', 'Szukaj ikony');
        emojiPickerSearch.addEventListener('input', renderEmojiPicker);
        searchWrap.appendChild(emojiPickerSearch);

        const clearButton = document.createElement('button');
        clearButton.type = 'button';
        clearButton.className = 'tasks-emoji-clear';
        clearButton.title = 'Usuń ikonę';
        clearButton.setAttribute('aria-label', 'Usuń ikonę');
        clearButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v5"/><path d="M14 11v5"/></svg>';
        clearButton.addEventListener('click', () => {
            setIconValue(activeIconInput, activeIconPicker, '');
            closeEmojiPicker();
            activeIconInput?.focus();
        });
        searchWrap.appendChild(clearButton);

        emojiPickerBody = document.createElement('div');
        emojiPickerBody.className = 'tasks-emoji-picker__body';

        emojiPicker.appendChild(tabs);
        emojiPicker.appendChild(searchWrap);
        emojiPicker.appendChild(emojiPickerBody);
        document.body.appendChild(emojiPicker);
        renderEmojiPicker();
        return emojiPicker;
    }

    function renderEmojiPicker() {
        if (!emojiPicker || !emojiPickerBody) return;
        const query = (emojiPickerSearch?.value || '').trim().toLowerCase();
        const tabs = emojiPicker.querySelectorAll('.tasks-emoji-picker__tabs button');
        tabs.forEach((tab, index) => tab.classList.toggle('is-active', index === activeIconSetIndex));

        emojiPickerBody.innerHTML = '';
        const searchResults = query
            ? normalizedProjectIconSearch.flatMap(set => set.items)
                .filter(item => item.icon.includes(query) || item.keywords.includes(query))
                .map(item => item.icon)
            : [];
        const sets = query
            ? [{ label: 'Wyniki', items: [...new Set(searchResults)] }]
            : [projectIconSets[activeIconSetIndex]];

        sets.forEach(set => {
            const group = document.createElement('section');
            group.className = 'tasks-emoji-group';
            const title = document.createElement('h3');
            title.textContent = set.label;
            const list = document.createElement('div');
            list.className = 'tasks-emoji-list';

            const items = set.items.length ? set.items : (query ? [query] : []);
            items.forEach(icon => {
                const option = document.createElement('button');
                option.type = 'button';
                option.className = 'tasks-emoji-option';
                option.textContent = icon;
                option.setAttribute('aria-label', `Wybierz ikonę ${icon}`);
                option.addEventListener('click', () => {
                    setIconValue(activeIconInput, activeIconPicker, icon);
                    closeEmojiPicker();
                    activeIconInput?.focus();
                });
                list.appendChild(option);
            });

            group.appendChild(title);
            group.appendChild(list);
            emojiPickerBody.appendChild(group);
        });
    }

    function openEmojiPicker(picker, input) {
        if (!picker || !input) return;
        createEmojiPicker();
        activeIconPicker = picker;
        activeIconInput = input;
        projectIconPickers.forEach(button => button.setAttribute('aria-expanded', String(button === picker)));
        emojiPickerSearch.value = '';
        renderEmojiPicker();
        emojiPicker.classList.add('is-open');
        setTimeout(() => emojiPickerSearch?.focus(), 30);
    }

    function closeEmojiPicker() {
        if (!emojiPicker) return;
        emojiPicker.classList.remove('is-open');
        projectIconPickers.forEach(button => button.setAttribute('aria-expanded', 'false'));
        activeIconPicker = null;
        activeIconInput = null;
    }

    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = value;
        return div.innerHTML;
    }

    if (createMenuToggle && createMenu) {
        createMenuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = createMenu.classList.toggle('is-open');
            createMenuToggle.setAttribute('aria-expanded', String(isOpen));
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
        });
    }

    if (statusFilterToggle && statusFilterMenu) {
        statusFilterToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !statusFilterMenu.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closePriorityFilterMenu();
            statusFilterMenu.classList.toggle('is-open', isOpen);
            statusFilterToggle.setAttribute('aria-expanded', String(isOpen));
        });

        statusFilterMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    if (priorityFilterToggle && priorityFilterMenu) {
        priorityFilterToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !priorityFilterMenu.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            priorityFilterMenu.classList.toggle('is-open', isOpen);
            priorityFilterToggle.setAttribute('aria-expanded', String(isOpen));
        });

        priorityFilterMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    if (sectionActionMenu) {
        const toggle = sectionActionMenu.querySelector('[data-section-menu-toggle]');
        const panel = sectionActionMenu.querySelector('.tasks-section-menu');

        toggle?.addEventListener('click', function(e) {
            e.stopPropagation();
            if (!panel) return;
            const isOpen = !sectionActionMenu.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            sectionActionMenu.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
        });

        sectionActionMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    projectActionMenus.forEach(menu => {
        const toggle = menu.querySelector('[data-project-menu-toggle]');
        if (!toggle) return;

        toggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !menu.classList.contains('is-open');
            closeProjectActionMenus(menu);
            closeCreateMenu();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            menu.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
        });

        menu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    });

    if (projectTree && projectTreeToggle) {
        setProjectTreeCollapsed(getProjectTreeCollapsed());

        projectTreeToggle.addEventListener('click', function(e) {
            e.preventDefault();

            const isCollapsed = !projectTree.classList.contains('is-collapsed');
            setProjectTreeCollapsed(isCollapsed);
            saveProjectTreeCollapsed(isCollapsed);
        });
    }

    if (projectNodes.length) {
        const collapsedProjects = getCollapsedProjects();

        projectNodes.forEach(projectNode => {
            const projectId = projectNode.dataset.projectId || '';
            const toggle = projectNode.querySelector('[data-project-collapse-toggle]');
            const shouldCollapse = collapsedProjects.has(projectId) && !projectNode.classList.contains('is-current');

            setProjectCollapsed(projectNode, shouldCollapse);

            toggle?.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                const isCollapsed = !projectNode.classList.contains('is-collapsed');
                setProjectCollapsed(projectNode, isCollapsed);

                if (projectId) {
                    if (isCollapsed) {
                        collapsedProjects.add(projectId);
                    } else {
                        collapsedProjects.delete(projectId);
                    }
                    saveCollapsedProjects(collapsedProjects);
                }
            });
        });
    }

    clearProjectTreeInitialState();

    document.querySelectorAll('[data-delete-project-form]').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const projectName = escapeHtml(this.dataset.projectName || 'ten projekt');

            window.showConfirmModal({
                title: 'Usuń projekt',
                message: `Czy na pewno chcesz usunąć projekt „${projectName}”? Zadania z projektu zostaną przeniesione do sekcji „Bez projektu”.`,
                confirmText: 'Usuń projekt',
                cancelText: 'Anuluj',
                confirmClass: 'btn-danger',
                onConfirm: () => this.submit()
            });
        });
    });

    document.querySelectorAll('[data-delete-section-form]').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const sectionName = escapeHtml(this.dataset.sectionName || 'tę grupę');

            window.showConfirmModal({
                title: 'Usuń grupę',
                message: `Czy na pewno chcesz usunąć grupę „${sectionName}”? Zadania z tej grupy zostaną przeniesione do sekcji „Bez projektu”.`,
                confirmText: 'Usuń grupę',
                cancelText: 'Anuluj',
                confirmClass: 'btn-danger',
                onConfirm: () => this.submit()
            });
        });
    });

    openProjectButtons.forEach(button => {
        button.addEventListener('click', () => {
            openModal(projectModal, projectNameInput, updateProjectSubmitState);
        });
    });

    openTagButtons.forEach(button => {
        button.addEventListener('click', () => {
            closeCreateMenu();
            openModal(tagModal, tagNameInput, updateTagSubmitState);
        });
    });

    openProjectRenameButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (projectRenameIdInput) projectRenameIdInput.value = button.dataset.projectId || '';
            if (projectRenameNameInput) projectRenameNameInput.value = button.dataset.projectName || '';
            if (projectRenameDescriptionInput) projectRenameDescriptionInput.value = button.dataset.projectDescription || '';
            if (projectRenameCodeInput) projectRenameCodeInput.value = button.dataset.projectCode || '';
            if (projectRenameIconInput) projectRenameIconInput.value = button.dataset.projectIcon || '';
            syncProjectIconPickers();
            closeProjectActionMenus();
            openModal(projectRenameModal, projectRenameNameInput, updateProjectRenameSubmitState);
            setTimeout(() => projectRenameNameInput?.select(), 60);
        });
    });

    openSectionCreateButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (sectionCreateProjectInput) sectionCreateProjectInput.value = button.dataset.projectId || '';
            if (sectionCreateTitleInput) sectionCreateTitleInput.value = '';
            if (sectionCreateDescriptionInput) sectionCreateDescriptionInput.value = '';
            if (sectionCreateIconInput) sectionCreateIconInput.value = '';
            syncProjectIconPickers();
            closeProjectActionMenus();
            openModal(sectionCreateModal, sectionCreateTitleInput, updateSectionCreateSubmitState);
        });
    });

    openSectionRenameButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (sectionRenameIdInput) sectionRenameIdInput.value = button.dataset.sectionId || '';
            if (sectionRenameTitleInput) sectionRenameTitleInput.value = button.dataset.sectionTitle || '';
            if (sectionRenameDescriptionInput) sectionRenameDescriptionInput.value = button.dataset.sectionDescription || '';
            if (sectionRenameIconInput) sectionRenameIconInput.value = button.dataset.sectionIcon || '';
            syncProjectIconPickers();
            closeSectionActionMenu();
            openModal(sectionRenameModal, sectionRenameTitleInput, updateSectionRenameSubmitState);
            setTimeout(() => sectionRenameTitleInput?.select(), 60);
        });
    });

    openIssueButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (button.disabled) return;
            syncIssuePickers();
            openModal(issueModal, issueTitleInput, updateIssueSubmitState);
        });
    });

    issueProjectPicker?.querySelector('[data-picker-toggle]')?.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = !issueProjectPicker.classList.contains('is-open');
        closeIssuePickers(issueProjectPicker);
        issueProjectPicker.classList.toggle('is-open', isOpen);
        this.setAttribute('aria-expanded', String(isOpen));
        if (isOpen) {
            resetPickerSearch(issueProjectPicker);
            setTimeout(() => issueProjectPicker.querySelector('[data-picker-search]')?.focus(), 30);
        }
    });

    issueSectionPicker?.querySelector('[data-picker-toggle]')?.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = !issueSectionPicker.classList.contains('is-open');
        closeIssuePickers(issueSectionPicker);
        issueSectionPicker.classList.toggle('is-open', isOpen);
        this.setAttribute('aria-expanded', String(isOpen));
        if (isOpen) {
            resetPickerSearch(issueSectionPicker);
            setTimeout(() => issueSectionPicker.querySelector('[data-picker-search]')?.focus(), 30);
        }
    });

    issueProjectOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.stopPropagation();
            selectIssueProject(this.dataset.projectId || '', this.dataset.defaultSectionId || '');
            closeIssuePickers();
        });
    });

    issueSectionOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.stopPropagation();
            selectIssueProject(this.dataset.sectionProjectId || '', this.dataset.sectionId || '');
            closeIssuePickers();
        });
    });

    issuePickerSearchInputs.forEach(input => {
        input.addEventListener('click', e => e.stopPropagation());
        input.addEventListener('input', function() {
            filterPickerSearch(this);
        });
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                e.stopPropagation();
                closeIssuePickers();
            }
        });
    });

    document.querySelectorAll('[data-close-modal]').forEach(button => {
        button.addEventListener('click', function() {
            closeModal(this.closest('.tasks-modal'));
        });
    });

    document.addEventListener('click', function(e) {
        if (createMenu && !createMenu.contains(e.target)) closeCreateMenu();
        if (!e.target.closest('[data-status-filter-menu]')) closeStatusFilterMenu();
        if (!e.target.closest('[data-priority-filter-menu]')) closePriorityFilterMenu();
        if (!e.target.closest('[data-section-actions]')) closeSectionActionMenu();
        if (!e.target.closest('[data-project-actions]')) closeProjectActionMenus();
        if (!e.target.closest('[data-issue-project-picker]') && !e.target.closest('[data-issue-section-picker]')) closeIssuePickers();
        if (emojiPicker && !emojiPicker.contains(e.target) && !e.target.closest('[data-project-icon-picker]')) {
            closeEmojiPicker();
        }
    });

    if (projectNameInput) {
        projectNameInput.addEventListener('input', function() {
            updateProjectSubmitState();
        });
    }

    if (tagNameInput) {
        tagNameInput.addEventListener('input', updateTagSubmitState);
        updateTagSubmitState();
    }

    if (projectForm) {
        const codeInput = projectForm.querySelector('[name="code"]');
        if (codeInput) {
            codeInput.addEventListener('input', function() {
                codeInput.dataset.touched = 'true';
            });
        }
        if (projectIconInput && !projectIconInput.value) {
            setIconValue(projectIconInput, getPickerForInput(projectIconInput), '');
        }
        if (projectIconInput) {
            projectIconInput.addEventListener('input', function() {
                setIconValue(projectIconInput, getPickerForInput(projectIconInput), projectIconInput.value);
            });
        }
        updateProjectSubmitState();
    }

    if (projectRenameIconInput) {
        projectRenameIconInput.addEventListener('input', function() {
            setIconValue(projectRenameIconInput, getPickerForInput(projectRenameIconInput), projectRenameIconInput.value);
        });
    }

    if (sectionCreateIconInput) {
        sectionCreateIconInput.addEventListener('input', function() {
            setIconValue(sectionCreateIconInput, getPickerForInput(sectionCreateIconInput), sectionCreateIconInput.value);
        });
    }

    if (sectionRenameIconInput) {
        sectionRenameIconInput.addEventListener('input', function() {
            setIconValue(sectionRenameIconInput, getPickerForInput(sectionRenameIconInput), sectionRenameIconInput.value);
        });
    }

    syncProjectIconPickers();

    projectIconPickers.forEach(picker => {
        picker.addEventListener('click', function(e) {
            e.stopPropagation();
            const input = document.getElementById(picker.dataset.projectIconTarget || '');
            if (!input) return;
            if (emojiPicker?.classList.contains('is-open') && activeIconPicker === picker) {
                closeEmojiPicker();
                return;
            }
            openEmojiPicker(picker, input);
        });
    });

    if (issueTitleInput) {
        issueTitleInput.addEventListener('input', updateIssueSubmitState);
        updateIssueSubmitState();
    }

    if (issueSectionSelect) {
        issueSectionSelect.addEventListener('change', syncIssuePickers);
        syncIssuePickers();
    }

    if (projectRenameNameInput) {
        projectRenameNameInput.addEventListener('input', updateProjectRenameSubmitState);
        updateProjectRenameSubmitState();
    }

    if (sectionCreateTitleInput) {
        sectionCreateTitleInput.addEventListener('input', updateSectionCreateSubmitState);
        updateSectionCreateSubmitState();
    }

    if (projectRenameCodeInput) {
        projectRenameCodeInput.addEventListener('input', function() {
            projectRenameCodeInput.value = projectRenameCodeInput.value.toUpperCase();
        });
    }

    if (sectionRenameTitleInput) {
        sectionRenameTitleInput.addEventListener('input', updateSectionRenameSubmitState);
        updateSectionRenameSubmitState();
    }

    document.querySelectorAll('.tasks-modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) closeModal(modal);
        });
        if (modal.classList.contains('is-open')) {
            let focusTarget = projectNameInput;
            let onOpen = updateProjectSubmitState;
            if (modal.id === 'issue-modal') {
                focusTarget = issueTitleInput;
                onOpen = updateIssueSubmitState;
            }
            if (modal.id === 'tag-modal') {
                focusTarget = tagNameInput;
                onOpen = updateTagSubmitState;
            }
            if (modal.id === 'project-rename-modal') {
                focusTarget = projectRenameNameInput;
                onOpen = updateProjectRenameSubmitState;
            }
            if (modal.id === 'section-create-modal') {
                focusTarget = sectionCreateTitleInput;
                onOpen = updateSectionCreateSubmitState;
            }
            if (modal.id === 'section-rename-modal') {
                focusTarget = sectionRenameTitleInput;
                onOpen = updateSectionRenameSubmitState;
            }
            openModal(modal, focusTarget, onOpen);
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeIssuePickers();
            closeEmojiPicker();
            const openModalEl = document.querySelector('.tasks-modal.is-open');
            if (openModalEl) closeModal(openModalEl);
        }
    });

    document.querySelectorAll('.tasks-toggle input').forEach(input => {
        input.addEventListener('change', function() {
            this.closest('.tasks-toggle')?.classList.toggle('is-on', this.checked);
        });
    });

    if (createMenuPanel) {
        createMenuPanel.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    function shouldIgnoreRowClick(event) {
        const cell = event.target.closest('td');
        return event.target.type === 'checkbox'
            || event.target.closest('form')
            || event.target.closest('input, button, select, textarea')
            || (cell && cell.querySelector('.task-checkbox'));
    }

    // Navigate to task detail on row click
    taskRows.forEach(row => {
        row.addEventListener('click', function(e) {
            if (this.dataset.dragSuppressClick === 'true') {
                delete this.dataset.dragSuppressClick;
                return;
            }
            if (shouldIgnoreRowClick(e)) {
                return;
            }
            const viewUrl = this.getAttribute('data-view-url');
            if (viewUrl) window.location.href = viewUrl;
        });
    });

    [...projectRows, ...sectionRows].forEach(row => {
        row.addEventListener('click', function(e) {
            if (shouldIgnoreRowClick(e)) return;
            const viewUrl = this.getAttribute('data-view-url');
            if (viewUrl) window.location.href = viewUrl;
        });

        row.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            if (shouldIgnoreRowClick(e)) return;
            const viewUrl = this.getAttribute('data-view-url');
            if (!viewUrl) return;
            e.preventDefault();
            window.location.href = viewUrl;
        });
    });

    function getDropStatus(dropTarget) {
        return dropTarget?.dataset.dropStatus || dropTarget?.closest('[data-drop-status]')?.dataset.dropStatus || '';
    }

    function updateTaskStatusVisual(row, status) {
        row.dataset.status = status;
        row.classList.toggle('completed', status === 'closed');

        const indicator = row.querySelector('.status-indicator');
        if (!indicator) return;

        Array.from(indicator.classList)
            .filter(className => className.startsWith('status-'))
            .forEach(className => indicator.classList.remove(className));
        indicator.classList.add(`status-${status}`);
        indicator.setAttribute('aria-label', statusLabels[status] || status);
    }

    function refreshGroupCounts() {
        document.querySelectorAll('.tasks-status-block, .tasks-status-subgroup').forEach(group => {
            const count = group.querySelectorAll('.task-row').length;
            const countEl = group.querySelector(':scope > header .tasks-rail-count');
            if (countEl) countEl.textContent = count;
        });
    }

    function moveTaskRow(row, dropTarget) {
        const status = getDropStatus(dropTarget);
        const list = dropTarget.matches('.tasks-issue-list, .tasks-status-subgroup-list')
            ? dropTarget
            : dropTarget.querySelector('.tasks-issue-list, .tasks-status-subgroup-list');

        if (!row || !status || !list || row.dataset.status === status) return;

        const previousParent = row.parentElement;
        const previousStatus = row.dataset.status;
        const taskId = row.dataset.taskId;

        row.dataset.dragSuppressClick = 'true';
        list.appendChild(row);
        updateTaskStatusVisual(row, status);
        refreshGroupCounts();
        applyFilters();

        fetch(`/tasks/update/${taskId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.getCookie('csrftoken')
            },
            body: JSON.stringify({ status })
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok || data.status !== 'success') {
                throw new Error(data.message || 'Błąd podczas aktualizacji statusu');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (previousParent) previousParent.appendChild(row);
            updateTaskStatusVisual(row, previousStatus);
            refreshGroupCounts();
            applyFilters();
            showMessage(error.message || 'Błąd podczas przenoszenia zadania', 'error');
        });
    }

    document.querySelectorAll('.tasks-issue-row[draggable="true"]').forEach(row => {
        row.addEventListener('dragstart', function(event) {
            this.classList.add('is-dragging');
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', this.dataset.taskId || '');
        });

        row.addEventListener('dragend', function() {
            this.classList.remove('is-dragging');
            document.querySelectorAll('.is-drag-over').forEach(target => target.classList.remove('is-drag-over'));
        });
    });

    document.querySelectorAll('[data-drop-status]').forEach(dropTarget => {
        dropTarget.addEventListener('dragover', function(event) {
            if (!Array.from(event.dataTransfer.types).includes('text/plain')) return;
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
            this.classList.add('is-drag-over');
        });

        dropTarget.addEventListener('dragleave', function(event) {
            if (!this.contains(event.relatedTarget)) {
                this.classList.remove('is-drag-over');
            }
        });

        dropTarget.addEventListener('drop', function(event) {
            event.preventDefault();
            this.classList.remove('is-drag-over');
            const taskId = event.dataTransfer.getData('text/plain');
            const row = document.querySelector(`.tasks-issue-row[data-task-id="${taskId}"]`);
            moveTaskRow(row, this);
        });
    });

    // Checkbox functionality
    function updateSelection() {
        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        // Exclude select-all checkbox from the count
        const selectedTaskCheckboxes = Array.from(selectedCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
        const count = selectedTaskCheckboxes.length;

        if (selectedCountSpan) {
            selectedCountSpan.textContent = `${count} wybranych`;
        }

        if (selectionActions) {
            if (count > 0) {
                selectionActions.style.visibility = 'visible';
                selectionActions.style.opacity = '1';
                
                // Show Edit only if exactly 1 is selected
                if (editBtn) {
                    editBtn.classList.toggle('u-hidden', count !== 1);
                }

                // Update Status Toggle Button
                if (statusToggleBtn) {
                    const statuses = Array.from(selectedTaskCheckboxes).map(cb => cb.closest('.task-row').dataset.status);
                    const anyOpen = statuses.some(s => s !== 'closed');
                    
                    if (anyOpen) {
                        statusToggleBtn.className = 'btn btn-secondary tasks-toolbar-btn';
                        statusToggleBtn.innerHTML = `
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                            Zamknij zadanie
                        `;
                        statusToggleBtn.dataset.targetStatus = 'closed';
                    } else {
                        statusToggleBtn.className = 'btn btn-secondary tasks-toolbar-btn';
                        statusToggleBtn.innerHTML = `
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                            Otwórz ponownie
                        `;
                        statusToggleBtn.dataset.targetStatus = 'reopened';
                    }
                }
            } else {
                selectionActions.style.visibility = 'hidden';
                selectionActions.style.opacity = '0';
            }
        }

        // Highlight rows
        checkboxes.forEach(cb => {
            const row = cb.closest('.task-row');
            if (row) {
                if (cb.checked) {
                    row.classList.add('checked');
                } else {
                    row.classList.remove('checked');
                }
            }
        });

        // Update select all state
        if (selectAllCheckbox) {
            const taskCheckboxes = Array.from(checkboxes).filter(cb => cb.id !== 'select-all-checkbox');
            selectAllCheckbox.checked = count === taskCheckboxes.length && taskCheckboxes.length > 0;
        }
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            checkboxes.forEach(cb => cb.checked = this.checked);
            updateSelection();
        });
    }

    checkboxes.forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
            updateSelection();
        });
    });

    // Initialize state
    updateSelection();

    // Edit selected task
    if (editBtn) {
        editBtn.addEventListener('click', function() {
            const selectedCheckbox = document.querySelector('.task-checkbox:checked');
            if (selectedCheckbox) {
                const taskId = selectedCheckbox.dataset.taskId;
                window.location.href = `/tasks/edit-task/${taskId}/`;
            }
        });
    }

    // Status Toggle selected tasks
    if (statusToggleBtn) {
        statusToggleBtn.addEventListener('click', function() {
            const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
            const taskIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.dataset.taskId));
            const targetStatus = this.dataset.targetStatus;
            const isClosing = targetStatus === 'closed';
            
            if (taskIds.length > 0) {
                window.showConfirmModal({
                    title: isClosing ? 'Zamknij zadania' : 'Otwórz ponownie zadania',
                    message: `Czy na pewno chcesz ${isClosing ? 'zamknąć' : 'ponownie otworzyć'} ${taskIds.length} ${taskIds.length === 1 ? 'zadanie' : 'zadań'}?`,
                    confirmText: isClosing ? 'Zamknij' : 'Otwórz ponownie',
                    cancelText: 'Anuluj',
                    confirmClass: isClosing ? 'btn-success' : 'btn-secondary',
                    onConfirm: () => {
                        fetch('/tasks/bulk-update-status/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': window.getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                task_ids: taskIds,
                                status: targetStatus
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                window.location.reload();
                            } else {
                                showMessage(data.message || 'Błąd podczas aktualizacji zadań', 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            showMessage('Błąd podczas aktualizacji zadań', 'error');
                        });
                    }
                });
            }
        });
    }

    // Delete selected tasks
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            
            const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
            const selectedTaskCheckboxes = Array.from(selectedCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
            const taskIds = selectedTaskCheckboxes.map(cb => {
                const row = cb.closest('.task-row');
                return row ? row.dataset.taskId : null;
            }).filter(id => id !== null);
            
            if (taskIds.length > 0) {
                window.showConfirmModal({
                    title: 'Potwierdź usunięcie',
                    message: `Czy na pewno chcesz usunąć ${taskIds.length} ${taskIds.length === 1 ? 'zadanie' : 'zadań'}? Tej operacji nie można cofnąć.`,
                    confirmText: 'Usuń',
                    cancelText: 'Anuluj',
                    confirmClass: 'btn-danger',
                    onConfirm: () => {
                        fetch('/tasks/delete/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': window.getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                task_ids: taskIds.map(id => parseInt(id))
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                selectedTaskCheckboxes.forEach(cb => {
                                    cb.closest('.task-row').remove();
                                });
                                updateSelection();
                                showMessage(data.message, 'success');
                            } else {
                                showMessage(data.message || 'Błąd podczas usuwania zadań', 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            showMessage('Błąd podczas usuwania zadań', 'error');
                        });
                    }
                });
            }
        });
    }

    // Filtering Logic
    function updateGroupVisibility() {
        groupRows.forEach(groupRow => {
            let hasVisibleTask = false;
            let nextRow = groupRow.nextElementSibling;

            while (nextRow && !nextRow.classList.contains('tasks-group-row')) {
                if (nextRow.classList.contains('task-row') && nextRow.style.display !== 'none') {
                    hasVisibleTask = true;
                    break;
                }
                nextRow = nextRow.nextElementSibling;
            }

            groupRow.style.display = hasVisibleTask ? '' : 'none';
        });

        statusSubgroups.forEach(group => {
            const visibleRows = Array.from(group.querySelectorAll('.task-row, .tasks-project-row, .tasks-section-row')).filter(row => row.style.display !== 'none');
            group.style.display = visibleRows.length ? '' : 'none';
        });

        issueGroups.forEach(group => {
            const visibleRows = Array.from(group.querySelectorAll('.task-row, .tasks-project-row, .tasks-section-row')).filter(row => row.style.display !== 'none');
            const hasEmptyState = group.querySelector('.tasks-empty-section, .tasks-empty-state') !== null;
            group.style.display = (visibleRows.length || hasEmptyState) ? '' : 'none';
        });
    }

    function getActiveStatusFilterValue() {
        const activeStatusButton = document.querySelector('[data-status-filter].is-active');
        return filterStatus ? filterStatus.value : (activeStatusButton?.dataset.statusFilter || '');
    }

    function getActivePriorityFilterValue() {
        const activePriorityButton = document.querySelector('[data-priority-filter].is-active');
        return filterPriority ? filterPriority.value : (activePriorityButton?.dataset.priorityFilter || '');
    }

    function setActiveFilterButtons() {
        const statusVal = getActiveStatusFilterValue();
        const priorityVal = getActivePriorityFilterValue();

        filterButtons.forEach(button => {
            if (button.dataset.statusFilter !== undefined) {
                button.classList.toggle('is-active', button.dataset.statusFilter === statusVal);
            }
            if (button.dataset.priorityFilter !== undefined) {
                button.classList.toggle('is-active', button.dataset.priorityFilter === priorityVal);
            }
        });

        if (statusFilterLabel) {
            const activeStatusButton = document.querySelector(`[data-status-filter="${statusVal}"]`);
            const label = activeStatusButton && statusVal ? getFilterButtonText(activeStatusButton) : '';
            statusFilterLabel.textContent = label ? `Stan: ${label}` : 'Stan';
        }

        if (statusFilterIcon) {
            statusFilterIcon.className = `status-indicator tasks-filter-status-icon ${statusVal ? `status-${statusVal}` : 'status-label-plain'}`;
        }

        if (priorityFilterLabel) {
            const activePriorityButton = document.querySelector(`[data-priority-filter="${priorityVal}"]`);
            const label = activePriorityButton && priorityVal ? getFilterButtonText(activePriorityButton) : '';
            priorityFilterLabel.textContent = label ? `Priorytet: ${label}` : 'Priorytet';
        }

        if (priorityFilterIcon) {
            priorityFilterIcon.innerHTML = getPriorityFilterIconMarkup(priorityVal);
        }
    }

    function applyFilters() {
        const statusVal = getActiveStatusFilterValue();
        const priorityVal = getActivePriorityFilterValue();
        const searchVal = filterSearch ? filterSearch.value.trim().toLowerCase() : '';

        taskRows.forEach(row => {
            const rowStatus = row.getAttribute('data-status');
            const rowPriority = row.getAttribute('data-priority');
            const rowText = row.textContent.toLowerCase();
            
            const matchesStatus = !statusVal || rowStatus === statusVal;
            const matchesPriority = !priorityVal || rowPriority === priorityVal;
            const matchesSearch = !searchVal || rowText.includes(searchVal);

            row.style.display = (matchesStatus && matchesPriority && matchesSearch) ? '' : 'none';
        });

        projectRows.forEach(row => {
            const rowText = row.textContent.toLowerCase();
            const matchesSearch = !searchVal || rowText.includes(searchVal);
            row.style.display = matchesSearch ? '' : 'none';
        });

        sectionRows.forEach(row => {
            const rowText = row.textContent.toLowerCase();
            const matchesSearch = !searchVal || rowText.includes(searchVal);
            row.style.display = matchesSearch ? '' : 'none';
        });

        updateGroupVisibility();
        setActiveFilterButtons();
    }

    if (filterStatus) filterStatus.addEventListener('change', applyFilters);
    if (filterPriority) filterPriority.addEventListener('change', applyFilters);
    if (filterSearch) filterSearch.addEventListener('input', applyFilters);

    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (this.dataset.statusFilter !== undefined && filterStatus) {
                filterStatus.value = this.dataset.statusFilter;
            }
            if (this.dataset.priorityFilter !== undefined && filterPriority) {
                filterPriority.value = this.dataset.priorityFilter;
            }
            if (this.dataset.statusFilter !== undefined && !filterStatus) {
                document.querySelectorAll('[data-status-filter]').forEach(btn => btn.classList.remove('is-active'));
                this.classList.add('is-active');
            }
            if (this.dataset.priorityFilter !== undefined && !filterPriority) {
                document.querySelectorAll('[data-priority-filter]').forEach(btn => btn.classList.remove('is-active'));
                this.classList.add('is-active');
            }
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            applyFilters();
        });
    });

    collapsibleGroupHeaders.forEach(header => {
        const button = header.querySelector('.tasks-group-caret');
        if (!button) return;

        button.addEventListener('click', function(event) {
            event.stopPropagation();
            const group = header.closest('.tasks-issue-group, .tasks-status-subgroup');
            if (!group) return;

            group.classList.toggle('is-collapsed');
            const isCollapsed = group.classList.contains('is-collapsed');
            button.setAttribute('aria-expanded', String(!isCollapsed));
            button.setAttribute('aria-label', isCollapsed ? 'Rozwiń sekcję' : 'Zwiń sekcję');
        });
    });

    applyFilters();

    // Helper functions


    function showMessage(message, type) {
        let container = document.querySelector('.notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        container.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('hiding');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
});
