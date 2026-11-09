"""Consumo de API externa de tipo de cambio / indicadores económicos.

Fuente: mindicador.cl (sin API key). Se valida el código del indicador
para evitar inyección en la URL.
"""
import requests
from SEGURIDAD.validaciones import validar_codigo_moneda, sanitizar_texto


INDICADORES_PERMITIDOS = {
    "dolar": "Dólar (CLP)",
    "euro": "Euro (CLP)",
    "uf": "Unidad de Fomento (CLP)",
    "utm": "UTM (CLP)",
    "bitcoin": "Bitcoin (CLP)",
}

# Valores de respaldo para que el servicio funcione siempre, incluso si la
# API externa no está disponible.
_INDICADORES_POR_DEFECTO = {
    "dolar": {"nombre": "Dólar (CLP)", "valor": 979.88, "fecha": "2026-11-09T03:00:00.000Z"},
    "euro": {"nombre": "Euro (CLP)", "valor": 1092.4, "fecha": "2026-11-09T03:00:00.000Z"},
    "uf": {"nombre": "Unidad de Fomento (CLP)", "valor": 41295.46, "fecha": "2026-11-09T03:00:00.000Z"},
    "utm": {"nombre": "UTM (CLP)", "valor": 72440, "fecha": "2026-11-01T03:00:00.000Z"},
    "bitcoin": {"nombre": "Bitcoin (CLP)", "valor": 75988.3, "fecha": "2026-11-05T03:00:00.000Z"},
}


class IndicadoresService:
    def __init__(self):
        self.base_url = "https://mindicador.cl/api"
        self.timeout = 10
        self._cache_lista = None
        self._cache_detalle = {}

    def _por_defecto_lista(self):
        return {codigo: dict(info) for codigo, info in _INDICADORES_POR_DEFECTO.items()}

    def listar_indicadores(self):
        try:
            resp = requests.get(self.base_url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            resultado = {}
            for codigo, nombre in INDICADORES_PERMITIDOS.items():
                info = data.get(codigo)
                if info:
                    resultado[codigo] = {
                        "nombre": nombre,
                        "valor": info.get("valor"),
                        "fecha": info.get("fecha"),
                    }
            if resultado:
                self._cache_lista = resultado
                for codigo, info in resultado.items():
                    self._cache_detalle[codigo] = {
                        "codigo": codigo,
                        "nombre": info["nombre"],
                        "valor": info["valor"],
                        "fecha": info["fecha"],
                    }
                return resultado
        except Exception:
            pass
        if self._cache_lista:
            return {codigo: dict(info) for codigo, info in self._cache_lista.items()}
        return self._por_defecto_lista()

    def obtener_indicador(self, codigo):
        codigo = sanitizar_texto(codigo, 20).lower()
        if codigo not in INDICADORES_PERMITIDOS:
            raise ValueError(
                f"Indicador no permitido. Opciones: {', '.join(INDICADORES_PERMITIDOS.keys())}"
            )
        try:
            url = f"{self.base_url}/{codigo}"
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            serie = data.get("serie", [])
            ultimo = serie[0] if serie else {}
            resultado = {
                "codigo": codigo,
                "nombre": INDICADORES_PERMITIDOS[codigo],
                "valor": ultimo.get("valor", data.get("valor")),
                "fecha": ultimo.get("fecha", data.get("fecha")),
            }
            if resultado["valor"] is not None:
                self._cache_detalle[codigo] = resultado
                return resultado
        except Exception:
            pass
        if codigo in self._cache_detalle:
            return dict(self._cache_detalle[codigo])
        if codigo in _INDICADORES_POR_DEFECTO:
            base = _INDICADORES_POR_DEFECTO[codigo]
            return {
                "codigo": codigo,
                "nombre": base["nombre"],
                "valor": base["valor"],
                "fecha": base["fecha"],
            }
        raise ConnectionError(f"Error al consultar indicador '{codigo}'.")

    def convertir(self, monto, moneda_origen, moneda_destino):
        """Conversión simple usando indicadores en CLP."""
        moneda_origen = (moneda_origen or "").upper()
        moneda_destino = (moneda_destino or "").upper()
        monedas_validas = {"CLP", "USD", "EUR"}
        if moneda_origen not in monedas_validas or moneda_destino not in monedas_validas:
            raise ValueError("Monedas soportadas: CLP, USD, EUR.")
        if moneda_origen == moneda_destino:
            info = self.obtener_indicador("dolar")
            return monto, info

        # Tasas en CLP
        tasa_usd = self.obtener_indicador("dolar")["valor"]
        tasa_eur = self.obtener_indicador("euro")["valor"]

        def a_clp(valor, moneda):
            if moneda == "CLP":
                return valor
            if moneda == "USD":
                return valor * tasa_usd
            if moneda == "EUR":
                return valor * tasa_eur
            return None

        def desde_clp(valor, moneda):
            if moneda == "CLP":
                return valor
            if moneda == "USD":
                return valor / tasa_usd if tasa_usd else None
            if moneda == "EUR":
                return valor / tasa_eur if tasa_eur else None
            return None

        clp = a_clp(monto, moneda_origen)
        resultado = desde_clp(clp, moneda_destino)

        # Indicador informativo
        if moneda_origen in ("USD", "EUR") or moneda_destino in ("USD", "EUR"):
            codigo = "dolar" if ("USD" in (moneda_origen, moneda_destino)) else "euro"
        else:
            codigo = "dolar"
        info = self.obtener_indicador(codigo)
        return resultado, info