from typing import List, Optional, Callable, Any
import re
from functools import wraps
from datetime import date

import requests
import markdown  # type: ignore
import click

from sitzungsexport.models import Protocol


class BookstackAPI:

    def authentication_needed(f: Callable[..., Any]): #type: ignore

        @wraps(f)
        def authentication_wrapper(*args, **kwargs):
            self = args[0]
            if not self.is_authenticated():
                self.authenticate()
            return f(*args, **kwargs)

        return authentication_wrapper

    def __init__(self, bookstack_url: str, username: str, password: str):
        self.bookstack_url: str = bookstack_url
        self.username: str = username
        self.password: str = password
        self.requests: requests.Session = requests.session()

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

    def save_protocol(self, protocol: Protocol, date: date) -> None:
        chapter_name = generate_semester_string(date)

        with click.progressbar(
            length=protocol.bteil_count + 1, label="Creating protocol(s)"
        ) as bar:

            if protocol.bteil_count != 0:
                for i, bteil in enumerate(protocol.bteile):
                    page_id = self.create_page(
                        name=f"Sitzung {date} B-Teil {i}",
                        book="sitzungsprotokolle-(b-teile)",
                        chapter=chapter_name,
                        text=bteil.content,
                    )
                    bar.update(1)
                    bteil.replacement = f"\n > {{{{@{page_id}}}}}\n"

            self.create_page(
                name=f"Sitzung {date}",
                book="sitzungsprotokolle",
                chapter=chapter_name,
                text=protocol.compile(),
            )
            bar.update(1)

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
