USUARIOS = {
    "Maxiclean": {
        "password": "maxiclean2024",
        "empresa": "ChemDry Zapopan",
        "sistema": "CRM Alonso",

        # 🔥 PLANTILLAS
        "plantillas": {
            "confirmacion": "Hola {nombre}, confirmamos tu servicio con {empresa} para hoy.",
            "seguimiento": "Hola {nombre}, hace tiempo que no realizas un servicio con {empresa}. ¿Te gustaría agendar?",
            "promocion": "Hola {nombre}, tenemos una promoción especial esta semana en {empresa}.",
            "agradecimiento": "Hola {nombre}, gracias por confiar en {empresa}. ¡Quedamos a tus órdenes!"
        },

        # 📊 SHEETS DE VENTAS (solo ID, aquí está bien)
        "sheets": {
            2022: "1L3wzHhc6_sN7h361uqXFI7lKzGobl_vtuHEDVTbCEdc",
            2023: "1e7B1Hp5zWJ3kLSS6d8CQoESYsaDWyIrFhIGcSRJE_Ag",
            2024: "1cVfveU9err9N6RI23OOHEABV8m8Rj9wRkO3F27o6TAg",
            2025: "1IodGW1K7c7GQBa90k6O8YCFOtwt3sA2PDFa7mmOkZ0E",
            2026: "1mqcHNhQEjEhKYYuY6iDOVpmPDH7br0VJITxdVx7wzls",
        },

        # 💰 SHEETS DE FINANZAS (🔥 ahora con URL completa + gid)
        # 💰 SHEETS DE FINANZAS — GIDs corregidos
        "finanzas": {
            2021: "https://docs.google.com/spreadsheets/d/1UYCOODvI1qqIMZK0Ub--xYLWuSpikLUPTv0O82dHidI/export?format=csv&gid=1421862808",
            2022: "https://docs.google.com/spreadsheets/d/1sJ0PhFEltEAmKGc9inDUlwFK19ItUzNiA4osKzdt4Cg/export?format=csv&gid=541909783",
            2023: "https://docs.google.com/spreadsheets/d/1K_DWpnkHiJ7YSbapkkhBdS-i4JUOXSphQD6MsihouQo/export?format=csv&gid=35758153",
            2024: "https://docs.google.com/spreadsheets/d/14ObgDv302X7mv4a43dwcfCjjYKyQzkBX9TnkKtRmGqM/export?format=csv&gid=1350430936",
            2025: "https://docs.google.com/spreadsheets/d/1mSNqzPw3nfZuTio-Kb-1So0gd2nUqrC1MAyMu4rUVkE/export?format=csv&gid=811298190",
            2026: "https://docs.google.com/spreadsheets/d/1VbfaboK2C1OZhRcsfq1uO8Xo6ZmeSN7Iyc6UeJby83s/export?format=csv&gid=1220405499",
        }
    },

    "Polla": {
        "password": "Pasteles12",
        "empresa": "Pasteles Lupita",
        "sistema": "CRM Alonso",

        # 🔥 PLANTILLAS PERSONALIZADAS
        "plantillas": {
            "confirmacion": "Hola {nombre}, tu pedido con {empresa} está confirmado 🎂",
            "seguimiento": "Hola {nombre}, ¿te gustaría hacer otro pedido con {empresa}?",
            "promocion": "Hola {nombre}, tenemos nuevos sabores en {empresa} 🍰",
            "agradecimiento": "Gracias por tu compra en {empresa}, {nombre} 🙌"
        },

        # 📊 SHEETS DE VENTAS
        "sheets": {
            2026: "ID_SHEET_TIA"
        },

        # 💰 FINANZAS (cuando tengas el sheet)
        "finanzas": {
            # Ejemplo:
            # 2026: "https://docs.google.com/spreadsheets/d/ID/export?format=csv&gid=XXXX"
        }
    }
}