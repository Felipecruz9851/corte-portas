"""Cliente HTTP para consulta direta ao ERP (192.168.0.6/pcp/op_abertura.php)."""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup


class ERPAuthenticationError(ValueError):
    """Levantada quando o PHPSESSID expirou ou usuário/senha são inválidos."""


class ERPConnectionError(ConnectionError):
    """Levantada quando há falha de rede ou HTTP ao comunicar com o ERP."""


class ERPClient:
    """Cliente síncrono para autenticação e consulta de OPs no ERP Líder."""

    BASE_URL = "http://192.168.0.6"
    OP_ABERTURA_URL = f"{BASE_URL}/pcp/op_abertura.php"
    LOGIN_URL = f"{BASE_URL}/home/login/"

    DEFAULT_HEADERS = {
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Origin": BASE_URL,
        "Referer": OP_ABERTURA_URL,
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/157.0.0.0 Safari/537.36"
        ),
    }

    def __init__(
        self,
        phpsessid: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.phpsessid = (phpsessid or "").strip()
        self.username = (username or "").strip()
        self.password = password or ""
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self._logged_in = False

        if self.phpsessid:
            self.session.cookies.set("PHPSESSID", self.phpsessid, domain="192.168.0.6")

    def login_with_credentials(self) -> str:
        """Autentica via /home/login/ e retorna o PHPSESSID obtido."""
        if not self.username or not self.password:
            raise ERPAuthenticationError(
                "Informe um PHPSESSID válido ou usuário e senha do ERP."
            )

        try:
            response = self.session.post(
                self.LOGIN_URL,
                data={
                    "pagina_acessada": f"{self.BASE_URL}/home/app",
                    "action": "login",
                    "usuario": self.username,
                    "senha": self.password,
                    "logar": "Acessar",
                },
                timeout=self.timeout,
                allow_redirects=True,
                verify=False,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise ERPConnectionError(
                f"Falha de conexão com o servidor ERP ({self.BASE_URL}): {exc}"
            ) from exc

        html_text = self._decode_response(response.content)
        soup = BeautifulSoup(html_text, "html.parser")
        alert = soup.find("div", class_=lambda c: c and "alert" in c.split())

        is_login_page = (
            response.url.rstrip("/").endswith("/home")
            or 'name="usuario"' in html_text
            or 'action="login"' in html_text
        )

        if alert:
            msg = alert.get_text(" ", strip=True)
            raise ERPAuthenticationError(
                f"Falha na autenticação com o ERP: {msg or 'Usuário ou senha incorretos.'}"
            )

        if is_login_page and not response.url.rstrip("/").endswith("/app"):
            raise ERPAuthenticationError(
                "Falha na autenticação com o ERP: Usuário ou senha incorretos."
            )

        self._logged_in = True
        self.phpsessid = self.session.cookies.get("PHPSESSID", "") or self.phpsessid
        return self.phpsessid

    def fetch_op_abertura(
        self,
        data: str,
        cod_empresa: str = "11",
        local: str = "PORTAS",
        item_desc: str = "S",
    ) -> str:
        """Executa POST em /pcp/op_abertura.php e retorna o HTML decodificado."""
        if self.username and self.password and not self._logged_in:
            self.login_with_credentials()
        elif not self.phpsessid:
            raise ERPAuthenticationError(
                "Sessão não informada. Forneça o cookie PHPSESSID ou usuário e senha."
            )

        payload = {
            "cod_empresa": (cod_empresa or "11").strip(),
            "data": (data or "").strip(),
            "local": (local or "PORTAS").strip(),
            "item_desc": (item_desc or "S").strip(),
        }

        try:
            response = self.session.post(
                self.OP_ABERTURA_URL,
                data=payload,
                headers={
                    **self.DEFAULT_HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=self.timeout,
                allow_redirects=True,
                verify=False,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise ERPConnectionError(
                f"Erro ao consultar {self.OP_ABERTURA_URL}: {exc}"
            ) from exc

        html_text = self._decode_response(response.content)
        if self._looks_like_login_or_expired(html_text, response.url):
            # Se tiver credenciais e ainda não tentou renovar, tenta uma vez.
            if self.username and self.password:
                self._logged_in = False
                self.login_with_credentials()
                return self.fetch_op_abertura(
                    data=data,
                    cod_empresa=cod_empresa,
                    local=local,
                    item_desc=item_desc,
                )
            raise ERPAuthenticationError(
                "Sessão expirada ou PHPSESSID inválido. "
                "Atualize o PHPSESSID ou autentique com usuário e senha do ERP."
            )

        return html_text

    @staticmethod
    def _decode_response(content: bytes) -> str:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("iso-8859-1", errors="replace")

    @staticmethod
    def _looks_like_login_or_expired(html_text: str, final_url: str) -> bool:
        upper = html_text.upper()
        if "LOCAL DE PRODU" in upper or "DATA DE ABERTURA" in upper:
            return False
        if (
            final_url.rstrip("/").endswith("/home")
            or 'name="usuario"' in html_text
            or 'name="senha"' in html_text
            or 'action="login"' in html_text
        ):
            return True
        return False
