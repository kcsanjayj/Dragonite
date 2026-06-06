"""
DAG builder and validator for the autonomous agent system.
Constructs and validates execution graphs (DAGs) from plans.
"""

from typing import Dict, List, Set, Optional
from collections import defaultdict, deque
from .types import Plan, Node, Edge, NodeStatus


class GraphBuilder:
    """
    Builds and validates execution DAGs from plans.
    Ensures acyclic graph structure and valid dependencies.
    """
    
    def __init__(self):
        """Initialize graph builder."""
        self.adjacency_list: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency_list: Dict[str, Set[str]] = defaultdict(set)
    
    def build_from_plan(self, plan: Plan) -> bool:
        """
        Build adjacency lists from a plan.
        
        Args:
            plan: The execution plan to build from
            
        Returns:
            True if build successful, False otherwise
        """
        self.adjacency_list.clear()
        self.reverse_adjacency_list.clear()
        
        # Build adjacency from nodes' dependencies
        for node_id, node in plan.nodes.items():
            for dep_id in node.dependencies:
                self.adjacency_list[dep_id].add(node_id)
                self.reverse_adjacency_list[node_id].add(dep_id)
        
        # Build adjacency from edges
        for edge in plan.edges:
            self.adjacency_list[edge.from_node].add(edge.to_node)
            self.reverse_adjacency_list[edge.to_node].add(edge.from_node)
        
        return True
    
    def validate_acyclic(self) -> bool:
        """
        Validate that the graph is acyclic (no cycles).
        
        Returns:
            True if graph is acyclic, False otherwise
        """
        visited = set()
        recursion_stack = set()
        
        def dfs(node: str) -> bool:
            """Depth-first search to detect cycles."""
            visited.add(node)
            recursion_stack.add(node)
            
            for neighbor in self.adjacency_list.get(node, set()):
                if neighbor not in visited:
                    if not dfs(neighbor):
                        return False
                elif neighbor in recursion_stack:
                    return False
            
            recursion_stack.remove(node)
            return True
        
        for node in self.adjacency_list:
            if node not in visited:
                if not dfs(node):
                    return False
        
        return True
    
    def validate_dependencies(self, plan: Plan) -> bool:
        """
        Validate that all node dependencies exist in the plan.
        
        Args:
            plan: The plan to validate
            
        Returns:
            True if all dependencies are valid, False otherwise
        """
        all_node_ids = set(plan.nodes.keys())
        
        for node_id, node in plan.nodes.items():
            for dep_id in node.dependencies:
                if dep_id not in all_node_ids:
                    return False
        
        return True
    
    def validate_plan(self, plan: Plan) -> tuple[bool, List[str]]:
        """
        Validate a plan completely.
        
        Args:
            plan: The plan to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check that plan has nodes
        if not plan.nodes:
            errors.append("Plan has no nodes")
        
        # Validate dependencies
        if not self.validate_dependencies(plan):
            errors.append("Plan contains invalid dependencies (missing nodes)")
        
        # Build graph
        self.build_from_plan(plan)
        
        # Validate acyclic
        if not self.validate_acyclic():
            errors.append("Plan contains cycles (not a DAG)")
        
        # Check for disconnected nodes - but allow nodes with no dependencies (entry points)
        all_node_ids = set(plan.nodes.keys())
        reachable = self._get_reachable_nodes()
        unreachable = all_node_ids - reachable
        
        # Only flag as error if unreachable nodes have dependencies (they should be connected)
        truly_disconnected = {nid for nid in unreachable if plan.nodes[nid].dependencies}
        if truly_disconnected:
            errors.append(f"Plan has disconnected nodes: {truly_disconnected}")
        
        return (len(errors) == 0, errors)
    
    def _get_reachable_nodes(self) -> Set[str]:
        """
        Get all nodes reachable from any node with no dependencies.
        
        Returns:
            Set of reachable node IDs
        """
        # Find nodes with no incoming edges (entry points)
        entry_points = set()
        for node_id in self.adjacency_list:
            if not self.reverse_adjacency_list.get(node_id, set()):
                entry_points.add(node_id)
        
        # If no entry points found, all nodes are entry points
        if not entry_points and self.adjacency_list:
            entry_points = set(self.adjacency_list.keys())
        
        # BFS from entry points
        visited = set()
        queue = deque(entry_points)
        
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            
            for neighbor in self.adjacency_list.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        
        return visited
    
    def get_execution_order(self, plan: Plan) -> List[str]:
        """
        Get a valid topological execution order for nodes.
        
        Args:
            plan: The plan to get execution order for
            
        Returns:
            List of node IDs in execution order
        """
        self.build_from_plan(plan)
        
        # Kahn's algorithm for topological sort
        in_degree = {node_id: 0 for node_id in plan.nodes.keys()}
        
        # Calculate in-degrees
        for node_id in plan.nodes.keys():
            in_degree[node_id] = len(self.reverse_adjacency_list.get(node_id, set()))
        
        # Initialize queue with nodes having in-degree 0
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        execution_order = []
        
        while queue:
            node = queue.popleft()
            execution_order.append(node)
            
            for neighbor in self.adjacency_list.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check if topological sort was successful (no cycles)
        if len(execution_order) != len(plan.nodes):
            raise ValueError("Cannot determine execution order: graph contains cycles")
        
        return execution_order
    
    def get_ready_nodes(self, plan: Plan) -> List[Node]:
        """
        Get nodes that are ready to execute (dependencies satisfied).
        
        Args:
            plan: The plan to check
            
        Returns:
            List of ready nodes
        """
        completed = {nid for nid, node in plan.nodes.items() if node.status == NodeStatus.COMPLETED}
        ready_nodes = []
        
        for node in plan.nodes.values():
            if node.status == NodeStatus.PENDING and node.dependencies.issubset(completed):
                ready_nodes.append(node)
        
        return ready_nodes
    
    def find_critical_path(self, plan: Plan) -> List[str]:
        """
        Find the critical path (longest path) in the DAG.
        
        Args:
            plan: The plan to analyze
            
        Returns:
            List of node IDs in the critical path
        """
        self.build_from_plan(plan)
        
        # Topological sort
        execution_order = self.get_execution_order(plan)
        
        # Calculate longest path to each node
        dist = {node_id: 0 for node_id in plan.nodes.keys()}
        prev = {node_id: None for node_id in plan.nodes.keys()}
        
        for node_id in execution_order:
            for neighbor in self.adjacency_list.get(node_id, set()):
                if dist[neighbor] < dist[node_id] + 1:
                    dist[neighbor] = dist[node_id] + 1
                    prev[neighbor] = node_id
        
        # Find the node with maximum distance
        max_dist = 0
        end_node = None
        for node_id, d in dist.items():
            if d > max_dist:
                max_dist = d
                end_node = node_id
        
        # Reconstruct the path
        critical_path = []
        current = end_node
        while current is not None:
            critical_path.append(current)
            current = prev[current]
        
        critical_path.reverse()
        return critical_path


class GraphValidator:
    """
    Validates execution graphs and plans.
    """
    
    def __init__(self):
        """Initialize graph validator."""
        self.builder = GraphBuilder()
    
    def validate(self, plan: Plan) -> tuple[bool, List[str]]:
        """
        Validate a plan.
        
        Args:
            plan: The plan to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return self.builder.validate_plan(plan)
    
    def validate_node(self, node: Node, plan: Plan) -> tuple[bool, List[str]]:
        """
        Validate a single node.
        
        Args:
            node: The node to validate
            plan: The plan containing the node
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check node ID
        if not node.id:
            errors.append("Node has no ID")
        
        # Check node type
        if not node.type:
            errors.append("Node has no type")
        
        # Check description
        if not node.description:
            errors.append("Node has no description")
        
        # Check dependencies exist
        all_node_ids = set(plan.nodes.keys())
        for dep_id in node.dependencies:
            if dep_id not in all_node_ids:
                errors.append(f"Node {node.id} has invalid dependency: {dep_id}")
        
        # Check for self-dependency
        if node.id in node.dependencies:
            errors.append(f"Node {node.id} depends on itself")
        
        return (len(errors) == 0, errors)
    
    def get_validation_summary(self, plan: Plan) -> Dict[str, any]:
        """
        Get a summary of the plan validation.
        
        Args:
            plan: The plan to validate
            
        Returns:
            Dictionary with validation summary
        """
        is_valid, errors = self.validate(plan)
        
        execution_order = []
        try:
            execution_order = self.builder.get_execution_order(plan)
        except ValueError:
            pass
        
        critical_path = []
        try:
            critical_path = self.builder.find_critical_path(plan)
        except ValueError:
            pass
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "total_nodes": len(plan.nodes),
            "total_edges": len(plan.edges),
            "execution_order": execution_order,
            "critical_path": critical_path,
            "critical_path_length": len(critical_path)
        }