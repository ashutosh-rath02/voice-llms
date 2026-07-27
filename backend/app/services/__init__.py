"""Business-action executors: the real side effects behind confirmed tool
executions. Each module registers its executor(s) with
app.agent.confirmation.register_executor on import; importing this package
(as app.agent.worker does) is what makes those registrations happen before a
call starts. Adding a new confirmable action (Phase 3c/3d/3e) means adding a
submodule here and importing it below — nothing else needs to change.
"""

from app.services import customers as customers  # noqa: F401  (import-for-side-effect)
