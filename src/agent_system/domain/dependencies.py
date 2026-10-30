"""Validate complete task graphs before scheduling or saving dependencies."""
from collections.abc import Mapping, Sequence
from uuid import UUID
from agent_system.domain.errors import DependencyError
from agent_system.domain.types import TaskStatus


def validate_graph(graph: Mapping[UUID, Sequence[UUID]]) -> None:
    indegree = {task: 0 for task in graph}
    dependents = {task: [] for task in graph}
    for task, dependencies in graph.items():
        if len(set(dependencies)) != len(dependencies):
            raise DependencyError("duplicate dependencies")
        for dependency in dependencies:
            if dependency not in graph:
                raise DependencyError(f"unknown dependency: {dependency}")
            indegree[task] += 1
            dependents[dependency].append(task)
    ready = [task for task, count in indegree.items() if count == 0]
    visited = 0
    while ready:
        task = ready.pop()
        visited += 1
        for dependent in dependents[task]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if visited != len(graph):
        raise DependencyError("dependency cycle detected")


def dependencies_complete(dependencies: Sequence[UUID], statuses: Mapping[UUID, TaskStatus]) -> bool:
    if any(task not in statuses for task in dependencies):
        raise DependencyError("unknown dependency")
    return all(statuses[task] == TaskStatus.COMPLETED for task in dependencies)
