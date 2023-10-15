from abc import ABC, abstractmethod, abstractproperty

from nskit.common.configuration import BaseConfiguration


class RepoClient(ABC):

    @abstractmethod
    def create(self, repo_name):
        pass

    @abstractmethod
    def get_remote_url(self, repo_name):
        pass

    @abstractmethod
    def delete(self, repo_name):
        pass

    @abstractmethod
    def check_exists(self, repo_name):
        pass

    @abstractmethod
    def list(self):
        pass


class VCSProviderSettings(ABC, BaseConfiguration):

    @abstractproperty
    def repo_client(self) -> RepoClient:
        raise NotImplementedError()
