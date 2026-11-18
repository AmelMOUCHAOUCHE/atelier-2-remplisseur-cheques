# Prompt envoyé au LLM (Claude)

Écris en Python 3 un module pos_communicator.py contenant une classe PosCommunicator qui dialogue avec une caisse via un port série (pyserial). Le constructeur reçoit le nom du port, le baudrate et le timeout. La méthode fetch_cheque_data() envoie "GET_CHEQUE_DATA\n", lit une ligne de réponse et applique ce protocole :
- "OK;YYYY-MM-DD;MONTANT\n" (ex. "OK;2026-11-16;145.50\n") : valider la date et le montant (strictement positif), puis retourner une dataclass ChequeData(date, amount) avec amount en Decimal ;
- "ERR_NO_TRANSACTION\n" -> lever NoTransactionError ; "ERR_BUSY\n" -> lever PosBusyError ;
- absence de réponse (timeout) -> PosTimeoutError ; trame vide ou malformée -> MalformedResponseError ; date ou montant invalide -> InvalidChequeDataError.
Toutes les exceptions héritent de PosCommunicationError et portent un message explicite.