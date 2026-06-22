# -*- coding: utf-8 -*-
"""Configuración compartida para scripts de TPM multipaís (BCCH)."""

FECHA_INICIO = "2005-01-01"

BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

ID_VARIABLE = 52  # Tasa de política monetaria

PAISES_CONFIG = [
    {"nombre": "Alemania", "codigo": "F019.TPM.TIN.GE.D", "id_pais": 276},
    {"nombre": "Argentina", "codigo": "F019.TPM.TIN.ARG.D", "id_pais": 32},
    {"nombre": "Australia", "codigo": "F019.TPM.TIN.AU.D", "id_pais": 36},
    {"nombre": "Brasil", "codigo": "F019.TPM.TIN.BRA.D", "id_pais": 76},
    {"nombre": "Canadá", "codigo": "F019.TPM.TIN.CA.D", "id_pais": 124},
    {"nombre": "Chile", "codigo": "F022.TPM.TIN.D001.NO.Z.D", "id_pais": 152},
    {"nombre": "China", "codigo": "F019.TPM.TIN.CHN.D", "id_pais": 156},
    {"nombre": "Colombia", "codigo": "F019.TPM.TIN.COL.D", "id_pais": 170},
    {"nombre": "Estados Unidos", "codigo": "F019.TPM.TIN.10.D", "id_pais": 840},
    {"nombre": "Filipinas", "codigo": "F019.TPM.TIN.PH.D", "id_pais": 608},
    {"nombre": "Francia", "codigo": "F019.TPM.TIN.FR.D", "id_pais": 250},
    {"nombre": "India", "codigo": "F019.TPM.TIN.IN.D", "id_pais": 356},
    {"nombre": "Indonesia", "codigo": "F019.TPM.TIN.ID.D", "id_pais": 360},
    {"nombre": "Japón", "codigo": "F019.TPM.TIN.30.D", "id_pais": 392},
    {"nombre": "Malasia", "codigo": "F019.TPM.TIN.MAL.D", "id_pais": 458},
    {"nombre": "México", "codigo": "F019.TPM.TIN.MEX.D", "id_pais": 484},
    {"nombre": "Nueva Zelanda", "codigo": "F019.TPM.TIN.NZ.D", "id_pais": 554},
    {"nombre": "Perú", "codigo": "F019.TPM.TIN.PER.D", "id_pais": 604},
    {"nombre": "Polonia", "codigo": "F019.TPM.TIN.POL.D", "id_pais": 616},
    {"nombre": "Reino Unido", "codigo": "F019.TPM.TIN.UK.D", "id_pais": 826},
    {"nombre": "República Checa", "codigo": "F019.TPM.TIN.RCH.D", "id_pais": 203},
    {"nombre": "Rusia", "codigo": "F019.TPM.TIN.RUS.D", "id_pais": 643},
    {"nombre": "Tailandia", "codigo": "F019.TPM.TIN.TAI.D", "id_pais": 764},
    {"nombre": "Turquía", "codigo": "F019.TPM.TIN.TUR.D", "id_pais": 792},
    {"nombre": "Zona Euro", "codigo": "F019.TPM.TIN.20.D", "id_pais": 1000},
]

# Países de la pantalla Política Monetaria (sin Uruguay: va por BCU en 034)
PAISES_LATAM_PM = [
    {"nombre": "Chile", "codigo": "F022.TPM.TIN.D001.NO.Z.D", "id_pais": 152},
    {"nombre": "Colombia", "codigo": "F019.TPM.TIN.COL.D", "id_pais": 170},
    {"nombre": "Perú", "codigo": "F019.TPM.TIN.PER.D", "id_pais": 604},
    {"nombre": "México", "codigo": "F019.TPM.TIN.MEX.D", "id_pais": 484},
]
