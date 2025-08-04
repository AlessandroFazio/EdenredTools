import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class UrlEqualityMode:
    scheme: bool = True
    netloc: bool = True
    path: bool = True
    fragment: bool = False
    query_params: Optional[List[str]] = None  # None = ignore, [] = ignore, list = selective compare


class Url:
    """
    A normalized, hashable representation of a URL with flexible equality and hashing semantics.
    You can control which parts of the URL matter for equality and hashing using `UrlEqualityMode`.
    """

    def __init__(self, parsed_url: urllib.parse.ParseResult, mode: UrlEqualityMode = UrlEqualityMode()) -> None:
        self._parsed_url = parsed_url
        self._mode = mode
        self.__params_cache: Optional[Dict[str, List[str]]] = None

    @property
    def _params(self) -> Dict[str, List[str]]:
        if self.__params_cache is None:
            self.__params_cache = urllib.parse.parse_qs(self._parsed_url.query, keep_blank_values=True)
        return self.__params_cache

    def _select_normalized_params(self) -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
        """
        Return a sorted, hashable representation of the selected query parameters.
        """
        if self._mode.query_params is None:
            return ()

        selected = {
            k: tuple(sorted(v))
            for k, v in self._params.items()
            if k in self._mode.query_params
        }
        return tuple(sorted(selected.items()))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Url) or self._mode != other._mode:
            return False

        return (
            (not self._mode.scheme or self._parsed_url.scheme == other._parsed_url.scheme) and
            (not self._mode.netloc or self._parsed_url.netloc == other._parsed_url.netloc) and
            (not self._mode.path or self._parsed_url.path == other._parsed_url.path) and
            (not self._mode.fragment or self._parsed_url.fragment == other._parsed_url.fragment) and
            (self._select_normalized_params() == other._select_normalized_params())
        )

    def __hash__(self) -> int:
        components = []
        if self._mode.scheme:
            components.append(self._parsed_url.scheme)
        if self._mode.netloc:
            components.append(self._parsed_url.netloc)
        if self._mode.path:
            components.append(self._parsed_url.path)
        if self._mode.fragment:
            components.append(self._parsed_url.fragment)
        if self._mode.query_params is not None:
            components.append(self._select_normalized_params())
        return hash(tuple(components))

    def __str__(self) -> str:
        return urllib.parse.urlunparse(self._parsed_url)

    def to_string(self) -> str:
        return str(self)
    
    def port(self) -> int:
        split = self._parsed_url.netloc.split(":", maxsplit=1)
        if len(split) == 1:
            if self._parsed_url.scheme == "http": 
                return 80
            elif self._parsed_url.scheme == "https": 
                return 443
            return -1
        return int(split[1])
    
    def hostname(self) -> str:
        split = self._parsed_url.netloc.split(":", maxsplit=1)
        return split[0]
    
    def path(self) -> str:
        return self._parsed_url.path

    def get_param(self, name: str) -> Optional[List[str]]:
        return self._params.get(name)

    def get_params(self) -> Dict[str, List[str]]:
        return dict(self._params)

    def without_params(self, *param_names: str) -> "Url":
        remaining = {k: v for k, v in self._params.items() if k not in param_names}
        new_query = urllib.parse.urlencode(remaining, doseq=True)
        return Url(self._parsed_url._replace(query=new_query), mode=self._mode)

    def with_params(self, **new_params: List[str]) -> "Url":
        merged = {**self._params, **new_params}
        new_query = urllib.parse.urlencode(merged, doseq=True)
        return Url(self._parsed_url._replace(query=new_query), mode=self._mode)

    def normalize_path(self) -> "Url":
        return Url(self._parsed_url._replace(path=self._parsed_url.path.rstrip('/')), mode=self._mode)

    def join(self, relative: str) -> "Url":
        return Url.from_string(urllib.parse.urljoin(str(self), relative), mode=self._mode)

    def get_base(self, include_path: bool = False) -> "Url":
        parts = dict(query='', fragment='', params='')
        if not include_path:
            parts['path'] = ''
        return Url(self._parsed_url._replace(**parts), mode=self._mode)

    def with_mode(self, mode: UrlEqualityMode) -> "Url":
        return Url(self._parsed_url, mode=mode)

    @classmethod
    def from_string(cls, url: str, mode: UrlEqualityMode = UrlEqualityMode()) -> "Url":
        return cls(urllib.parse.urlparse(url), mode=mode)
