USUARIOS = {
    "Maxiclean": {
        "password": "maxiclean2024",
        "empresa": "MaxiClean ChemDry",
        "sistema": "CRM Alonso",

        # 🔥 APP
        "app": {
            "nombre": "CRM Dashboard",
            "icono": "🧹",
            "titulo_login": "CRM Alonso",
            "logo": "assets/chemdry-logo.png"
        },

        # 🔥 PLANTILLAS
        "plantillas": {
            "confirmacion": "Hola {nombre}, confirmamos tu servicio con {empresa} para hoy.",
            "seguimiento": "Hola {nombre}, hace tiempo que no realizas un servicio con {empresa}. ¿Te gustaría agendar?",
            "promocion": "Hola {nombre}, tenemos una promoción especial esta semana en {empresa}.",
            "agradecimiento": "Hola {nombre}, gracias por confiar en {empresa}. ¡Quedamos a tus órdenes!"
        },

        # 📊 SHEETS DE VENTAS
        "sheets": {
            2022: "1L3wzHhc6_sN7h361uqXFI7lKzGobl_vtuHEDVTbCEdc",
            2023: "1e7B1Hp5zWJ3kLSS6d8CQoESYsaDWyIrFhIGcSRJE_Ag",
            2024: "1cVfveU9err9N6RI23OOHEABV8m8Rj9wRkO3F27o6TAg",
            2025: "1IodGW1K7c7GQBa90k6O8YCFOtwt3sA2PDFa7mmOkZ0E",
            2026: "1mqcHNhQEjEhKYYuY6iDOVpmPDH7br0VJITxdVx7wzls",
        },

        # 💰 SHEETS DE FINANZAS
        "finanzas": {
            2021: "https://docs.google.com/spreadsheets/d/1UYCOODvI1qqIMZK0Ub--xYLWuSpikLUPTv0O82dHidI/export?format=csv&gid=1585340803",
            2022: "https://docs.google.com/spreadsheets/d/1sJ0PhFEltEAmKGc9inDUlwFK19ItUzNiA4osKzdt4Cg/export?format=csv&gid=1738265014",
            2023: "https://docs.google.com/spreadsheets/d/1K_DWpnkHiJ7YSbapkkhBdS-i4JUOXSphQD6MsihouQo/export?format=csv&gid=1832931943",
            2024: "https://docs.google.com/spreadsheets/d/14ObgDv302X7mv4a43dwcfCjjYKyQzkBX9TnkKtRmGqM/export?format=csv&gid=123077403",
            2025: "https://docs.google.com/spreadsheets/d/1mSNqzPw3nfZuTio-Kb-1So0gd2nUqrC1MAyMu4rUVkE/export?format=csv&gid=811298190",
            2026: "https://docs.google.com/spreadsheets/d/1VbfaboK2C1OZhRcsfq1uO8Xo6ZmeSN7Iyc6UeJby83s/export?format=csv&gid=1220405499",
        },

        # 🗂️ CATEGORÍAS DE SERVICIOS
        "categorias": {
            "Alfombra": ["alfombra"],
            "Sala": ["sala"],
            "Colchon": ["colchón", "colchon"],
            "Tapete": ["tapete"],
            "Sillas": ["silla"],
            "Interior auto": ["auto", "interior"],
            "Futon": ["futón", "futon"],
        },

        # 🔴 NORMALIZACIÓN DE ORIGEN
        "origenes": {
            "int": "Internet",
            "internet": "Internet",
            "rep": "Repetición",
            "repeticion": "Repetición",
            "rec": "Recomendación",
            "recomendacion": "Recomendación",
            "ref": "Recomendación",
            "face": "Facebook",
            "amigo": "Amigo",
            "amigos": "Amigo",
            "club": "Club",
            "primo": "Primo",
            "maristas": "Maristas"
        },

        # 💰 COTIZADOR
        "cotizador": {
            "paquetes": ["Healthy", "Premium", "Protección", "Ecológico", "Sencillo"],
            "minimo": 950,
            "intro": "Hola muchas gracias.\nEn breve:\nChemDry es una franquicia americana con presencia en todos los continentes, por ende nuestros productos son de la más alta calidad a nivel mundial. No usamos jabones, solo una solución Natural* a base de bicarbonatos, la cual ayuda a usar muy poca agua y esto ayuda a que los muebles sequen más rápido.",
            "purt_descripcion": "Adicional al paquete que ud escoja, si la mancha de orina tiene mucho tiempo o huele mucho, quizá sea necesario poner un producto llamado PURT (por sus siglas en inglés) el cual rompe la molécula de la urea, que es la responsable del olor y debe secar sola, tardando aproximadamente 8-10 horas. Los técnicos estando en su domicilio le dirán después de lavar si es necesario poner este producto, cuyo costo es de $540.00\nCon este producto se empapa el mueble y se deja penetrar lo mismo que penetró la orina y se deja actuar solito hasta que seque y así se desintegra la urea.",
            "purt_costo": 540,
            "descripcion_paquetes": {
                "Sencillo": "-Aspirado profundo\n-Pre rociado y cepillado\n-Limpieza con la solución Natural y cepillado\n-Desmanchado",
                "Ecológico": "-Aspirado profundo\n-Pre rociado y cepillado\n-Limpieza con la solución Natural y cepillado\n-Desmanchado\n+DESINFECCIÓN",
                "Protección": "-Aspirado profundo\n-Pre rociado y cepillado\n-Limpieza con la solución Natural y cepillado\n-Desmanchado\n+PROTECCIÓN (con Teflon)",
                "Premium": "-Aspirado profundo\n-Pre rociado y cepillado\n-Limpieza con la solución Natural y cepillado\n-Desmanchado\n+DESINFECCIÓN\n+PROTECCIÓN (con Teflon)",
                "Healthy": "-Aspirado profundo\n-Pre rociado y cepillado\n-Limpieza con la solución Natural y cepillado\n-Desmanchado\n+DESINFECCIÓN\n+PROTECCIÓN (con Teflon)\n+ANTIACAROS"
            },
            "descuentos_paquete": {
                "Sencillo": 0,
                "Ecológico": 5,
                "Protección": 10,
                "Premium": 10,
                "Healthy": 12
            },
            "cierre": "Es un servicio que toma como 2-3 hrs y tarda como 8-10 hr en secar.\nGracias por la confianza y quedo en espera de su respuesta\nSaludos cordiales,",
            "firma": "Carmen Alonso\nMaxi Clean Chem Dry",
            "servicios_cantidad": [
                "Alfombra (por m2)",
                "Tapete Oriental / Lana",
                "Tapete Sintético",
                "Tapete Seda o Algodón",
                "Mampara (por m2)"
            ],
            "servicios_plazas": [
                "Mueble - Asiento y Respaldo Fijos",
                "Mueble - Solo Asiento o Respaldo",
                "Mueble - Asiento + Respaldo Removible",
                "Mueble - Chaise Lounge",
                "Taburete / Puff",
                "Reposet o Recliner"
            ],
            "servicios_sillas": [
                "Silla de Oficina (tela)",
                "Sillón Ejecutivo (tela)",
                "Silla Comedor - Solo Asiento o Respaldo (tela)",
                "Silla Comedor - Asiento + Respaldo (tela)"
            ],
            "precios": {
                "Alfombra (por m2)": {"Healthy": 127, "Premium": 91, "Protección": 76, "Ecológico": 57, "Sencillo": 49},
                "Tapete Oriental / Lana": {"Healthy": 413, "Premium": 359, "Protección": 328, "Ecológico": 254, "Sencillo": 235},
                "Tapete Sintético": {"Healthy": 232, "Premium": 196, "Protección": 167, "Ecológico": 149, "Sencillo": 132},
                "Tapete Seda o Algodón": {"Healthy": 659, "Premium": 625, "Protección": 587, "Ecológico": 454, "Sencillo": 375},
                "Mueble - Asiento y Respaldo Fijos": {"Healthy": 526, "Premium": 434, "Protección": 382, "Ecológico": 274, "Sencillo": 202},
                "Mueble - Solo Asiento o Respaldo": {"Healthy": 583, "Premium": 515, "Protección": 417, "Ecológico": 308, "Sencillo": 245},
                "Mueble - Asiento + Respaldo Removible": {"Healthy": 649, "Premium": 568, "Protección": 485, "Ecológico": 362, "Sencillo": 289},
                "Mueble - Chaise Lounge": {"Healthy": 656, "Premium": 559, "Protección": 455, "Ecológico": 369, "Sencillo": 281},
                "Taburete / Puff": {"Healthy": 306, "Premium": 251, "Protección": 203, "Ecológico": 138, "Sencillo": 99},
                "Reposet o Recliner": {"Healthy": 691, "Premium": 581, "Protección": 486, "Ecológico": 372, "Sencillo": 308},
                "Silla de Oficina (tela)": {"Healthy": 220, "Premium": 179, "Protección": 149, "Ecológico": 125, "Sencillo": 116},
                "Sillón Ejecutivo (tela)": {"Healthy": 304, "Premium": 233, "Protección": 202, "Ecológico": 165, "Sencillo": 161},
                "Silla Comedor - Solo Asiento o Respaldo (tela)": {"Healthy": 153, "Premium": 123, "Protección": 108, "Ecológico": 87, "Sencillo": 78},
                "Silla Comedor - Asiento + Respaldo (tela)": {"Healthy": 220, "Premium": 160, "Protección": 136, "Ecológico": 111, "Sencillo": 104},
                "Mampara (por m2)": {"Healthy": 135, "Premium": 101, "Protección": 83, "Ecológico": 72, "Sencillo": 67},
                "Auto Pequeño (Tsuru, Ikon, Chevy)": {"Healthy": 2163, "Premium": 1906, "Protección": 1617, "Ecológico": 1370, "Sencillo": 1283},
                "Auto Mediano (Jetta, Accord, Focus)": {"Healthy": 2312, "Premium": 2163, "Protección": 1854, "Ecológico": 1597, "Sencillo": 1539},
                "Auto Grande (Lincoln, Cadillac)": {"Healthy": 2575, "Premium": 2266, "Protección": 2009, "Ecológico": 1751, "Sencillo": 1742},
                "Camioneta (hasta 3 filas)": {"Healthy": 2781, "Premium": 2575, "Protección": 2369, "Ecológico": 2163, "Sencillo": 2228},
                "Camioneta Pick Up": {"Healthy": 1920, "Premium": 1755, "Protección": 1527, "Ecológico": 1299, "Sencillo": 1452},
                "Camioneta Pick Up Doble Cabina": {"Healthy": 2313, "Premium": 2093, "Protección": 1813, "Ecológico": 1521, "Sencillo": 1553},
                "Colchón Cuna / Corral": {"Healthy": 631, "Premium": 529, "Protección": 493, "Ecológico": 368, "Sencillo": 324},
                "Colchón Individual": {"Healthy": 1177, "Premium": 1065, "Protección": 896, "Ecológico": 734, "Sencillo": 648},
                "Colchón Matrimonial": {"Healthy": 1464, "Premium": 1179, "Protección": 1115, "Ecológico": 915, "Sencillo": 821},
                "Colchón Queen Size": {"Healthy": 1563, "Premium": 1381, "Protección": 1239, "Ecológico": 1050, "Sencillo": 974},
                "Colchón King Size": {"Healthy": 1757, "Premium": 1555, "Protección": 1391, "Ecológico": 1154, "Sencillo": 1026},
            }
        }
    },

    "Polla": {
        "password": "Pasteles12",
        "empresa": "Pasteles Lupita",
        "sistema": "CRM Alonso",

        # 🔥 APP
        "app": {
            "nombre": "CRM Dashboard",
            "icono": "🎂",
            "titulo_login": "CRM Pasteles Lupita",
            "logo": None
        },

        # 🔥 PLANTILLAS
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

        # 💰 FINANZAS
        "finanzas": {},

        # 🗂️ CATEGORÍAS DE SERVICIOS
        "categorias": {
            "Pasteles": ["pastel"],
            "Cupcakes": ["cupcake"],
            "Galletas": ["galleta"],
            "Otros": []
        },

        # 🔴 NORMALIZACIÓN DE ORIGEN
        "origenes": {
            "int": "Internet",
            "internet": "Internet",
            "rep": "Repetición",
            "rec": "Recomendación",
            "face": "Facebook",
            "ig": "Instagram",
            "instagram": "Instagram",
            "wa": "WhatsApp",
            "whatsapp": "WhatsApp",
        },

        # 💰 COTIZADOR
        "cotizador": {
            "paquetes": [],
            "minimo": 0,
            "intro": "Hola, muchas gracias por contactarnos.",
            "purt_descripcion": "",
            "purt_costo": 0,
            "descripcion_paquetes": {},
            "descuentos_paquete": {},
            "cierre": "Gracias por su preferencia.\nSaludos cordiales,",
            "firma": "Pasteles Lupita",
            "servicios_cantidad": [],
            "servicios_plazas": [],
            "servicios_sillas": [],
            "precios": {}
        }
    }
}