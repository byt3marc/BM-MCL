from __future__ import annotations

from collections.abc import Callable
from typing import final

from PySide6.QtCore import Property, QObject, QThread, Signal, Slot

from core.auth.microsoft import AuthError, MicrosoftAuthService
from core.auth.models import Account
from core.auth.offline import InvalidUsernameError, create_offline_account
from core.auth.store import AuthStore, AuthStoreError


@final
class _MicrosoftAuthWorker(QObject):
    completed = Signal(dict)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        service: MicrosoftAuthService,
        authorization_url: str | None = None,
        account: Account | None = None,
    ) -> None:
        super().__init__()
        self._service = service
        self._authorization_url = authorization_url
        self._account = account

    @Slot()
    def run(self) -> None:
        try:
            if self._authorization_url is not None:
                account = self._service.complete_login(self._authorization_url)
            elif self._account is not None:
                account = self._service.refresh_account(self._account)
            else:
                raise AuthError("No hay una operación de Microsoft pendiente.")
            self.completed.emit(account.to_dict())
        except (AuthError, ValueError) as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


@final
class AuthBridge(QObject):
    accountsChanged = Signal(list)
    selectedAccountChanged = Signal(dict)
    accountChanged = Signal(dict)
    loginSuccess = Signal(dict)
    loginError = Signal(str)
    loginInProgressChanged = Signal()

    def __init__(
        self,
        store: AuthStore,
        microsoft_service: MicrosoftAuthService | None = None,
    ) -> None:
        super().__init__()
        self.store: AuthStore = store
        self.microsoft_service: MicrosoftAuthService = microsoft_service or MicrosoftAuthService()
        self._accounts: list[Account] = self.store.load_accounts()
        self._threads: set[QThread] = set()
        self._login_in_progress: bool = False

    @Property(list, notify=accountsChanged)
    def accounts(self) -> list[dict[str, object]]:
        return [account.to_dict() for account in self._accounts]

    @Property(dict, notify=selectedAccountChanged)
    def selectedAccount(self) -> dict[str, object]:
        account = self._get_selected_account()
        return account.to_dict() if account is not None else {}

    @Property(bool, notify=loginInProgressChanged)
    def loginInProgress(self) -> bool:
        return self._login_in_progress

    @Slot(result=list)
    def getAccounts(self) -> list[dict[str, object]]:
        return [account.to_dict() for account in self._accounts]

    @Slot(str, result=dict)
    def loginOffline(self, username: str) -> dict[str, object]:
        try:
            account = create_offline_account(username)
            self._store_account(account, select=True)
        except (InvalidUsernameError, AuthStoreError) as error:
            self.loginError.emit(str(error))
            return {}
        account_data = account.to_dict()
        self.loginSuccess.emit(account_data)
        return account_data

    @Slot(result=str)
    def getLoginUrl(self) -> str:
        try:
            return self.microsoft_service.get_login_url()
        except AuthError as error:
            self.loginError.emit(str(error))
            return ""

    @Slot(str)
    def completeMicrosoftLogin(self, authorization_url: str) -> None:
        if self._login_in_progress:
            self.loginError.emit("Ya hay un inicio de sesión de Microsoft en curso.")
            return
        self._login_in_progress = True
        self.loginInProgressChanged.emit()
        worker = _MicrosoftAuthWorker(self.microsoft_service, authorization_url=authorization_url)
        self._start_worker(worker, self._on_microsoft_account)

    @Slot(str)
    def refreshAccount(self, account_uuid: str) -> None:
        if self._login_in_progress:
            self.loginError.emit("Ya hay una operación de Microsoft en curso.")
            return
        account = self._find_account(account_uuid)
        if account is None:
            self.loginError.emit("La cuenta seleccionada no existe.")
            return
        self._login_in_progress = True
        self.loginInProgressChanged.emit()
        worker = _MicrosoftAuthWorker(self.microsoft_service, account=account)
        self._start_worker(worker, self._on_microsoft_account)

    @Slot(str, result=bool)
    def selectAccount(self, account_uuid: str) -> bool:
        account = self._find_account(account_uuid)
        if account is None:
            self.loginError.emit("La cuenta seleccionada no existe.")
            return False
        try:
            self.store.set_selected_uuid(account.uuid)
        except AuthStoreError as error:
            self.loginError.emit(str(error))
            return False
        self.selectedAccountChanged.emit(account.to_dict())
        self.accountChanged.emit(account.to_dict())
        return True

    @Slot(str, result=bool)
    def removeAccount(self, account_uuid: str) -> bool:
        account = self._find_account(account_uuid)
        if account is None:
            return False
        try:
            self.store.remove(account_uuid)
        except AuthStoreError as error:
            self.loginError.emit(str(error))
            return False
        self._accounts = [stored for stored in self._accounts if stored.uuid != account_uuid]
        self.accountsChanged.emit(self.accounts)
        selected = self._get_selected_account()
        self.selectedAccountChanged.emit(selected.to_dict() if selected is not None else {})
        return True

    def _start_worker(
        self,
        worker: _MicrosoftAuthWorker,
        on_completed: Callable[[dict[str, object]], None],
    ) -> None:
        thread = QThread(self)
        _ = worker.moveToThread(thread)
        _ = thread.started.connect(worker.run)
        _ = worker.completed.connect(on_completed)
        _ = worker.failed.connect(self.loginError.emit)
        _ = worker.finished.connect(thread.quit)
        _ = worker.finished.connect(worker.deleteLater)
        _ = thread.finished.connect(thread.deleteLater)
        _ = thread.finished.connect(lambda: self._finish_worker(thread))
        self._threads.add(thread)
        thread.start()

    @Slot(dict)
    def _on_microsoft_account(self, account_data: dict[str, object]) -> None:
        try:
            account = Account.from_dict(account_data)
            self._store_account(account, select=True)
        except (ValueError, AuthStoreError) as error:
            self.loginError.emit(str(error))
            return
        data = account.to_dict()
        self.loginSuccess.emit(data)

    def _finish_worker(self, thread: QThread) -> None:
        self._threads.discard(thread)
        self._login_in_progress = False
        self.loginInProgressChanged.emit()

    def _store_account(self, account: Account, select: bool) -> None:
        self.store.add_or_update(account)
        if select:
            self.store.set_selected_uuid(account.uuid)
        existing_index = next(
            (index for index, stored in enumerate(self._accounts) if stored.uuid == account.uuid),
            None,
        )
        if existing_index is None:
            self._accounts.append(account)
        else:
            self._accounts[existing_index] = account
        account_data = account.to_dict()
        self.accountsChanged.emit(self.accounts)
        self.selectedAccountChanged.emit(account_data)
        self.accountChanged.emit(account_data)

    def get_selected_account(self) -> Account | None:
        return self._get_selected_account()

    def _get_selected_account(self) -> Account | None:
        try:
            selected_uuid = self.store.get_selected_uuid()
        except AuthStoreError:
            return None
        return self._find_account(selected_uuid) if selected_uuid is not None else None

    def _find_account(self, account_uuid: str | None) -> Account | None:
        if account_uuid is None:
            return None
        return next((account for account in self._accounts if account.uuid == account_uuid), None)
