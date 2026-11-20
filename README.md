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