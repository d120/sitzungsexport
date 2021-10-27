import re
from abc import ABC
from datetime import date
from functools import wraps
from typing import Any, Callable, List, Optional

import click
import markdown
import requests

from sitzungsexport.models import Protocol


class WikiInterface(ABC):
    def __init__(self, bookstack_url: str, username: str, password: str):
        self.bookstack_url: str = bookstack_url
        self.username: str = username
        self.password: str = password
        self.requests: requests.Session = requests.session()

    def save_protocol(self, protocol: Protocol, date: date) -> None:
        chapter_name = generate_semester_string(date)

        with click.progressbar(
            length=protocol.bteil_count + 1, label="Creating protocol(s)"
        ) as bar:

            if protocol.bteil_count != 0:
                for i, bteil in enumerate(protocol.bteile):
                    page_id = self.create_page(
                        name=f"Sitzung {date} B-Teil {i}",
                        book="Sitzungsprotokolle (B-Teile)",
                        chapter=chapter_name,
                        text=bteil.content,
                    )
                    bar.update(1)
                    bteil.replacement = f"\n > {{{{@{page_id}}}}}\n"

            self.create_page(
                name=f"Sitzung {date}",
                book="Sitzungsprotokolle",
                chapter=chapter_name,
                text=protocol.compile(),
            )
            bar.update(1)

    def create_page(
        self, name: str, book: str, chapter: Optional[str], text: str
    ) -> int:
        pass

    def chapter_exists(self, book: str, chapter: str) -> bool:
        pass


class ScrapeAPI(WikiInterface):
    def authentication_needed(f: Callable[..., Any]):  # type: ignore
        @wraps(f)
        def authentication_wrapper(*args, **kwargs):
            self = args[0]
            if not self.is_authenticated():
                self.authenticate()
            return f(*args, **kwargs)

        return authentication_wrapper

    def authenticate(self):
        url = urljoin(self.bookstack_url, "login")
        login_page = self.requests.get(url)
        login_post = self.requests.post(
            url,
            data={
                "username": self.username,
                "password": self.password,
                "_token": get_token(login_page.text),
            },
        )
        # if we were not redirected from the login page, the login was unsuccessful
        if login_post.url.split("/")[-1] == "login":
            raise RuntimeError("Login failed, was redirected to login url.")

    @authentication_needed
    def create_page(
        self, name: str, book: str, chapter: Optional[str], text: str
    ) -> int:
        create_url = ""
        if chapter:
            if not self.chapter_exists(book, chapter):
                self.create_chapter(name=chapter, book=book, description=None)
            create_url = urljoin(
                self.bookstack_url,
                "books",
                sanitize(book),
                "chapter",
                sanitize(chapter),
                "create-page",
            )
        else:
            create_url = urljoin(
                self.bookstack_url, "books", sanitize(book), "create-page"
            )
        if self.page_exists(book, name):
            raise RuntimeError(f'Page "{name}" already exists')
        submission_form = self.requests.get(create_url)
        self.requests.post(
            submission_form.url,
            data={
                "name": name,
                "markdown": text,
                "html": markdown.markdown(text, extensions=["tables", "sane_lists"]),
                "_token": get_token(submission_form.text),
            },
        )
        return int(submission_form.url.split("/")[-1])

    @authentication_needed
    def create_chapter(self, name: str, book: str, description: Optional[str]) -> None:
        create_url = urljoin(
            self.bookstack_url, "books", sanitize(book), "create-chapter"
        )
        submission_form = self.requests.get(create_url)
        if not description:
            description = ""
        self.requests.post(
            submission_form.url,
            data={
                "name": name,
                "description": description,
                "_token": get_token(submission_form.text),
            },
        )

    def is_authenticated(self) -> bool:
        login_url = urljoin(self.bookstack_url, "login")
        res = self.requests.get(login_url)
        if res.url.split("/")[-1] == "login":
            return False
        return True

    @authentication_needed
    def chapter_exists(self, book: str, chapter: str) -> bool:
        if (
            self.requests.get(
                urljoin(
                    self.bookstack_url,
                    "books",
                    sanitize(book),
                    "chapter",
                    sanitize(chapter),
                )
            ).status_code
            != 200
        ):
            return False
        return True

    @authentication_needed
    def page_exists(self, book: str, page: str) -> bool:
        if (
            self.requests.get(
                urljoin(
                    self.bookstack_url, "books", sanitize(book), "page", sanitize(page)
                )
            ).status_code
            != 200
        ):
            return False
        print(
            urljoin(self.bookstack_url, "books", sanitize(book), "page", sanitize(page))
        )
        return True


class BookstackAPI(WikiInterface):
    def __init__(self, bookstack_url: str, username: str, password: str):
        super().__init__(bookstack_url, username, password)
        self._headers = {"Authorization": f"Token {username}:{password}"}

    def create_page(
        self, name: str, book: str, chapter: Optional[str], text: str
    ) -> int:
        book_id = self.get_book_id(book)
        if not book_id:
            raise RuntimeError("Book does not exist.")
        chapter_id = None
        if chapter:
            chapter_id = self.get_chapter_id(book_id=book_id, chaptername=chapter)
            if not chapter_id:
                chapter_id = self.create_chapter(book_id=book_id, name=chapter)
                if not chapter_id:
                    raise RuntimeError("Chapter does not exist.")

        page = requests.post(
            urljoin(self.bookstack_url, "api", "pages"),
            data={
                "book_id": book_id,
                "chapter_id": chapter_id,
                "name": name,
                "markdown": text,
            },
            headers=self._headers,
        )
        if page.status_code != 200:
            raise RuntimeError(f"Page could not be created, error was: {page.text}")
        return page.json()["id"]

    def create_chapter(self, book_id: int, name: str) -> Optional[int]:
        res = requests.post(
            urljoin(self.bookstack_url, "api", "chapters"),
            data={"book_id": book_id, "name": name},
            headers=self._headers,
        )
        if res.status_code != 200:
            return None
        return res.json()["id"]

    def get_book_id(self, bookname: str) -> Optional[int]:
        book = requests.get(
            f"{self.bookstack_url}/api/books",
            headers=self._headers,
            params={
                "filter[name:eq]": bookname,
            },
        ).json()
        if book["total"] != 1:
            return None
        return book["data"][0]["id"]

    def get_chapter_id(self, book_id: int, chaptername: str) -> Optional[int]:
        chapter = requests.get(
            f"{self.bookstack_url}/api/chapters",
            headers=self._headers,
            params={
                "filter[book_id:eq]": str(book_id),
                "filter[name:eq]": chaptername,
            },
        ).json()
        if chapter["total"] != 1:
            return None
        return chapter["data"][0]["id"]


# helper functions


def get_token(html: str) -> str:
    form_fields = re.search(
        '<input type="hidden" name="_token" value="(?P<token>.*)">', html
    )
    if not form_fields:
        raise RuntimeError("No token found in page")
    return form_fields["token"]


def generate_semester_string(date: date) -> str:
    if 4 <= date.month < 10:
        return f"Sommersemester {date.year}"
    if date.month < 4:
        return f"Wintersemester {date.year - 1}/{date.year}"
    return f"Wintersemester {date.year}/{date.year + 1}"


def sanitize(entity: str) -> str:
    return entity.replace(" ", "-").replace("/", "").lower()


def urljoin(*args) -> str:
    return "/".join(args)
