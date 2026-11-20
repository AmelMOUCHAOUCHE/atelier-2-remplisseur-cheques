# Remplisseur de chèques - module de communication POS

Atelier 2 - Tests unitaires (Amel MOUCHAOUCHE, Vainepuana LEMAIRE)

## Installation (Windows, invite de commandes)
py -m venv .venv
.venv\Scripts\activate
pip install pyserial pytest pytest-cov mutmut

## Tests unitaires
pytest -v

## Couverture (lignes + branches)
pytest --cov=src --cov-branch --cov-report=term-missing --cov-report=html

## Tests de mutation (Linux : GitHub Codespaces ou WSL)
rm -rf mutants
mutmut run
mutmut results

## Analyse de la dépendance (étape 3)
Dans le code généré, le constructeur créait directement `serial.Serial(port, ...)` :
la classe ouvrait un vrai port COM et ne pouvait pas être testée sans caisse branchée
(dépendance externe et non déterministe).
Solution : inversion de contrôle. Une interface `SerialPort` (méthodes `write` et
`readline`) est injectée dans le constructeur. En production on passe
`serial.Serial("COM3", 9600, timeout=2)`, en test un stub (`unittest.mock.Mock`).