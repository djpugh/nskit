from abc import ABC, abstractmethod, abstractproperty
from typing import List

from pydantic import HttpUrl

from nskit.common.configuration import BaseConfiguration


class RepoClient(ABC):

    @abstractmethod
    def create(self, repo_name):
        pass

    @abstractmethod
    def get_remote_url(self, repo_name) -> HttpUrl:
        pass

    @abstractmethod
    def delete(self, repo_name):
        pass

    @abstractmethod
    def check_exists(self, repo_name) -> bool:
        pass

    @abstractmethod
    def list(self) -> List[str]:
        pass


class VCSProviderSettings(ABC, BaseConfiguration):

    @abstractproperty
    def repo_client(self) -> RepoClient:
        raise NotImplementedError()
