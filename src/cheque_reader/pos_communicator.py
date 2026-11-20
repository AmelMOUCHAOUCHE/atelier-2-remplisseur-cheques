"""Module de communication avec la caisse (POS) pour le remplisseur de chèques."""
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol



class PosCommunicationError(Exception):
    """Erreur de base pour toute erreur de communication avec la caisse."""


class NoTransactionError(PosCommunicationError):
    """Aucun paiement par chèque en cours."""


class PosBusyError(PosCommunicationError):
    """La caisse est occupée."""


class PosTimeoutError(PosCommunicationError):
    """Aucune réponse de la caisse dans le délai imparti."""


class MalformedResponseError(PosCommunicationError):
    """Trame vide, illisible ou ne respectant pas le protocole."""


class InvalidChequeDataError(PosCommunicationError):
    """Date ou montant invalide dans une trame bien formée."""

class SerialPort(Protocol):
    """Ce dont PosCommunicator a besoin pour dialoguer avec la caisse.

    serial.Serial (pyserial) respecte déjà cette interface.
    """

    def write(self, data: bytes) -> int: ...

    def readline(self) -> bytes: ...

@dataclass(frozen=True)
class ChequeData:
    date: date
    amount: Decimal

DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
AMOUNT_PATTERN = re.compile(r"\d+(\.\d{1,2})?")
MAX_AMOUNT = Decimal("999999.99")  # exigence FCT-VAL-01 (atelier 1)


class PosCommunicator:
    REQUEST = b"GET_CHEQUE_DATA\n"

    def __init__(self, port: SerialPort):
        self.serial = port

    def fetch_cheque_data(self) -> ChequeData:
        self.serial.write(self.REQUEST)
        raw = self.serial.readline()

        if not raw:
            raise PosTimeoutError("Aucune réponse de la caisse (timeout)")

        try:
            line = raw.decode("ascii").strip()
        except UnicodeDecodeError:
            raise MalformedResponseError("Trame non ASCII")

        if line == "ERR_NO_TRANSACTION":
            raise NoTransactionError("Aucune transaction chèque en cours")
        if line == "ERR_BUSY":
            raise PosBusyError("Caisse occupée")

        parts = line.split(";")
        if len(parts) != 3 or parts[0] != "OK":
            raise MalformedResponseError(f"Trame malformée : {line!r}")

        if not DATE_PATTERN.fullmatch(parts[1]):
            raise InvalidChequeDataError(f"Format de date invalide : {parts[1]!r}")
        try:
            cheque_date = datetime.strptime(parts[1], "%Y-%m-%d").date()
        except ValueError:
            raise InvalidChequeDataError(f"Date inexistante : {parts[1]!r}")

        if not AMOUNT_PATTERN.fullmatch(parts[2]):
            raise InvalidChequeDataError(f"Format de montant invalide : {parts[2]!r}")
        amount = Decimal(parts[2])
        if amount <= 0 or amount > MAX_AMOUNT:
            raise InvalidChequeDataError(f"Montant hors bornes : {amount}")

        return ChequeData(date=cheque_date, amount=amount)