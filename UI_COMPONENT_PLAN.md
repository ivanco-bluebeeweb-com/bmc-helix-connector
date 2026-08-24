# BMC Helix Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `bmc-helix-connector`.

## 0. Разница с IDEAL_ONBOARDING.md
Идеал предполагает мгновенную проверку через реальный вызов `/api/jwt/login` прямо в
форме подключения. Реализация делает это тем же способом, что и другие token-based
коннекторы портфеля — `connect_bmc_helix` сам выполняет пробный логин перед сохранением,
и форма показывает результат через стандартный error/success путь `ui.Form`.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Stack`(v) + `ui.Text`(host label) + `ui.Divider` + `ui.Button`×5 (Incidents/Problems/Changes/Work Orders/CMDB) + `ui.Button`("App settings") | Без карточек, без дублирования инструкций. |
| Connect form (not connected) | `ui.Form` + labelled `ui.Input`×3 (host, username, password) + `ui.Button`("Where do I find my AR REST host?" → help panel) | Одна простая форма — единственный режим аутентификации. |
| Help panel | `ext.panel`(center_overlay=True) + `ui.Text`(объяснение формата host + qualification-синтаксиса) | Единственное место с инструкциями подключения. |
| Incidents list (center, `center_overlay=True`) | `ui.Header` + `ui.Select`(status filter) + `ui.DataTable`(id/summary/status/priority) + row action → detail | Табличный список инцидентов. |
| Incident detail | `ui.Stack`(v) + labelled `ui.Text`×N + `ui.Form`(update_incident: status/priority Select) | Обновление статуса/приоритета прямо из детали. |
| Problems/Changes/Work Orders panels | Аналогичная структура `ui.DataTable` + create `ui.Form` | Единый паттерн по всем ITSM-сущностям. |
| CMDB panel | `ui.DataTable`(CI name/class/status) | Просмотр конфигурационных единиц. |
| Generic form passthrough | `ui.Form`(form name + qualification query) → `ui.DataTable` | Доступ к любой AR System форме, не покрытой типизированными функциями. |
| App settings | `ext.panel`(center_overlay=True) + список подключённых хостов + `ui.Button`("Disconnect") | Управление подключениями отдельно от sidebar. |

## 2. Правила
- Инпуты всегда с лейблами (`_field` helper), плейсхолдеры контекстные (реальный формат хоста/полей AR System).
- Форма подключения растянута на всю ширину левого сайдбара, содержимое — на всю ширину формы.
- Инструкции живут только в help panel модалке, не дублируются в sidebar.
