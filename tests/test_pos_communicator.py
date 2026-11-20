"""Tests unitaires de PosCommunicator (1 classe testée = 1 classe de test)."""
import re
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from cheque_reader.pos_communicator import (
    ChequeData,
    InvalidChequeDataError,
    MalformedResponseError,
    NoTransactionError,
    PosBusyError,
    PosCommunicationError,
    PosCommunicator,
    PosTimeoutError,
    SerialPort,
)


def make_communicator(response: bytes):
    """Arrange commun : un stub de port série qui renvoie `response`."""
    port = Mock(spec=SerialPort)
    port.readline.return_value = response
    return PosCommunicator(port), port


class TestPosCommunicator:
    # ---------- Cas nominal ----------

    def test_reponse_ok_retourne_les_donnees_du_cheque(self):
        # Arrange
        communicator, _ = make_communicator(b"OK;2026-11-16;145.50\n")
        # Act
        result = communicator.fetch_cheque_data()
        # Assert
        assert result == ChequeData(date=date(2026, 11, 16), amount=Decimal("145.50"))

    def test_envoie_la_requete_une_seule_fois(self):
        # Arrange
        communicator, port = make_communicator(b"OK;2026-11-16;145.50\n")
        # Act
        communicator.fetch_cheque_data()
        # Assert (mock : on vérifie l'interaction avec la dépendance)
        port.write.assert_called_once_with(b"GET_CHEQUE_DATA\n")
        port.readline.assert_called_once_with()

    def test_accepte_une_fin_de_ligne_windows(self):
        communicator, _ = make_communicator(b"OK;2026-11-16;145.50\r\n")
        assert communicator.fetch_cheque_data().amount == Decimal("145.50")

    def test_accepte_un_montant_sans_decimales(self):
        communicator, _ = make_communicator(b"OK;2026-11-16;145\n")
        assert communicator.fetch_cheque_data().amount == Decimal("145")

    # ---------- Cas extrêmes ----------

    def test_accepte_le_29_fevrier_d_une_annee_bissextile(self):
        communicator, _ = make_communicator(b"OK;2028-02-29;10.00\n")
        assert communicator.fetch_cheque_data().date == date(2028, 2, 29)

    def test_accepte_le_plus_petit_montant(self):
        communicator, _ = make_communicator(b"OK;2026-11-16;0.01\n")
        assert communicator.fetch_cheque_data().amount == Decimal("0.01")

    def test_accepte_le_montant_maximum(self):
        communicator, _ = make_communicator(b"OK;2026-11-16;999999.99\n")
        assert communicator.fetch_cheque_data().amount == Decimal("999999.99")

    # ---------- Erreurs renvoyées par la caisse ----------

    def test_err_no_transaction_leve_no_transaction_error(self):
        communicator, _ = make_communicator(b"ERR_NO_TRANSACTION\n")
        with pytest.raises(NoTransactionError, match=r"^Aucune transaction chèque en cours$"):
            communicator.fetch_cheque_data()

    def test_err_busy_leve_pos_busy_error(self):
        communicator, _ = make_communicator(b"ERR_BUSY\n")
        with pytest.raises(PosBusyError, match=r"^Caisse occupée$"):
            communicator.fetch_cheque_data()

    # ---------- Timeout / trame vide ----------

    def test_absence_de_reponse_leve_timeout(self):
        # pyserial renvoie b"" quand le timeout expire
        communicator, _ = make_communicator(b"")
        with pytest.raises(PosTimeoutError, match=r"^Aucune réponse de la caisse \(timeout\)$"):
            communicator.fetch_cheque_data()

    def test_ligne_vide_leve_malformed(self):
        communicator, _ = make_communicator(b"\n")
        with pytest.raises(MalformedResponseError):
            communicator.fetch_cheque_data()

    # ---------- Trames malformées ----------

    @pytest.mark.parametrize("response", [
        b"OK;2026-11-16\n",                # champ manquant
        b"OK;2026-11-16;145.50;extra\n",   # champ en trop
        b"OK,2026-11-16,145.50\n",         # mauvais séparateur
        b"ok;2026-11-16;145.50\n",         # statut en minuscules
        b"KO;2026-11-16;145.50\n",         # statut inconnu
        b"ERR_UNKNOWN\n",                  # erreur non prévue
        
    ])

    def test_trame_malformee_leve_malformed(self, response):
        communicator, _ = make_communicator(response)
        line = response.decode().strip()
        with pytest.raises(MalformedResponseError, match=f"^Trame malformée : {re.escape(repr(line))}$"):
            communicator.fetch_cheque_data()

    
    def test_octets_non_ascii_levent_malformed(self):
        communicator, _ = make_communicator(b"\xff\xfe\x00\n")
        with pytest.raises(MalformedResponseError, match=r"^Trame non ASCII$"):
            communicator.fetch_cheque_data()
            

    # ---------- Dates invalides ----------

    @pytest.mark.parametrize("bad_date", [
        "2027-02-29",   # 29 février d'une année non bissextile
        "2026-02-30",   # jour inexistant
        "2026-13-01",   # mois 13
        "2026-00-10",   # mois 0
        "16/11/2026",   # mauvais format
        "2026-1-5",     # mois et jour sans zéro
        "",             # date vide
    ])
    def test_date_invalide_leve_invalid_cheque_data(self, bad_date):
        communicator, _ = make_communicator(f"OK;{bad_date};145.50\n".encode())
        with pytest.raises(InvalidChequeDataError, match=f"^(Format de date invalide|Date inexistante) : {re.escape(repr(bad_date))}$"):
            communicator.fetch_cheque_data()

    # ---------- Montants invalides ----------

    @pytest.mark.parametrize("bad_amount", [
        "0",           # nul
        "0.00",        # nul avec décimales
        "-5.00",       # négatif
        "abc",         # non numérique
        "145,50",      # virgule au lieu du point
        "145.505",     # 3 décimales
        "1000000.00",  # au-dessus du maximum
        "NaN",         # valeur spéciale
        "Infinity",    # valeur spéciale
        "1e3",         # notation scientifique
        "",            # montant vide
    ])
    def test_montant_invalide_leve_invalid_cheque_data(self, bad_amount):
        communicator, _ = make_communicator(f"OK;2026-11-16;{bad_amount}\n".encode())
        with pytest.raises(InvalidChequeDataError, match=r"^(Format de montant invalide|Montant hors bornes) : .+$"):
            communicator.fetch_cheque_data()

    # ---------- Hiérarchie des exceptions ----------

    @pytest.mark.parametrize("response", [b"ERR_BUSY\n", b"", b"OK;x;1\n"])
    def test_toutes_les_erreurs_heritent_de_pos_communication_error(self, response):
        communicator, _ = make_communicator(response)
        with pytest.raises(PosCommunicationError):
            communicator.fetch_cheque_data()