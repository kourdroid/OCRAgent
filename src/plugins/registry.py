from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from src.plugins.base import DEFAULT_CLIENT_ID, ClientPlugin, WorkflowPlugin
from src.plugins.morocco_import import MoroccoImportDossierWorkflow
from src.plugins.supply_chain import SupplyChainPlugin


class UnknownClientPluginError(ValueError):
    def __init__(self, client_id: str) -> None:
        super().__init__(f"Unknown client plugin: {client_id}")
        self.client_id = client_id


class UnknownWorkflowPluginError(ValueError):
    def __init__(self, workflow_id: str) -> None:
        super().__init__(f"Unknown workflow plugin: {workflow_id}")
        self.workflow_id = workflow_id


def normalize_client_id(value: str | None) -> str:
    client_id = (value or DEFAULT_CLIENT_ID).strip()
    return client_id or DEFAULT_CLIENT_ID


@dataclass(frozen=True)
class ClientPluginRegistry:
    plugins: Mapping[str, ClientPlugin]

    def get(self, client_id: str | None) -> ClientPlugin:
        normalized_client_id = normalize_client_id(client_id)
        plugin = self.plugins.get(normalized_client_id)
        if plugin is None:
            raise UnknownClientPluginError(normalized_client_id)
        return plugin

    def list(self) -> list[ClientPlugin]:
        return list(self.plugins.values())


@dataclass(frozen=True)
class ClientConfig:
    client_id: str
    display_name: str
    workflow_id: str
    provider_profile: str
    ruleset_version: str
    enabled_modules: tuple[str, ...]


@dataclass(frozen=True)
class ClientConfigRegistry:
    clients: Mapping[str, ClientConfig]

    def get(self, client_id: str | None) -> ClientConfig:
        normalized_client_id = normalize_client_id(client_id)
        config = self.clients.get(normalized_client_id)
        if config is None:
            raise UnknownClientPluginError(normalized_client_id)
        return config


@dataclass(frozen=True)
class WorkflowPluginRegistry:
    workflows: Mapping[str, WorkflowPlugin]

    def get(self, workflow_id: str) -> WorkflowPlugin:
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            raise UnknownWorkflowPluginError(workflow_id)
        return workflow


DEFAULT_PLUGIN_REGISTRY = ClientPluginRegistry(
    plugins={
        DEFAULT_CLIENT_ID: SupplyChainPlugin(),
        "supply_chain": SupplyChainPlugin(
            client_id="supply_chain",
            display_name="Supply Chain",
        ),
    }
)

DEFAULT_CLIENT_CONFIG_REGISTRY = ClientConfigRegistry(
    clients={
        DEFAULT_CLIENT_ID: ClientConfig(
            client_id=DEFAULT_CLIENT_ID,
            display_name="Default Demo",
            workflow_id="invoice_3way",
            provider_profile="cloud_default",
            ruleset_version="1",
            enabled_modules=("invoice", "schema_review", "reconciliation"),
        ),
        "supply_chain": ClientConfig(
            client_id="supply_chain",
            display_name="Supply Chain",
            workflow_id="invoice_3way",
            provider_profile="cloud_default",
            ruleset_version="1",
            enabled_modules=("invoice", "schema_review", "reconciliation"),
        ),
        "delassus": ClientConfig(
            client_id="delassus",
            display_name="Delassus",
            workflow_id="morocco_import_dossier",
            provider_profile="cloud_default",
            ruleset_version="1",
            enabled_modules=("dossiers", "evidence_review", "reports"),
        ),
    }
)

DEFAULT_WORKFLOW_REGISTRY = WorkflowPluginRegistry(
    workflows={
        "morocco_import_dossier": MoroccoImportDossierWorkflow(),
    }
)


def get_client_plugin(client_id: str | None) -> ClientPlugin:
    return DEFAULT_PLUGIN_REGISTRY.get(client_id)


def get_client_config(client_id: str | None) -> ClientConfig:
    return DEFAULT_CLIENT_CONFIG_REGISTRY.get(client_id)


def get_workflow_plugin(workflow_id: str) -> WorkflowPlugin:
    return DEFAULT_WORKFLOW_REGISTRY.get(workflow_id)
