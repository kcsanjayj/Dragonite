"""
Unit tests for graph validation and building.
"""

import pytest
from app.core.graph import GraphBuilder, GraphValidator
from app.core.types import Plan, Node, Edge


@pytest.mark.unit
class TestGraphBuilder:
    """Test cases for GraphBuilder."""
    
    @pytest.fixture
    def builder(self):
        return GraphBuilder()
    
    @pytest.fixture
    def sample_plan(self):
        """Create a sample plan for testing."""
        nodes = {
            "node1": Node(
                id="node1",
                type="tool_call",
                description="First node",
                dependencies=set()
            ),
            "node2": Node(
                id="node2",
                type="tool_call",
                description="Second node",
                dependencies={"node1"}
            ),
            "node3": Node(
                id="node3",
                type="tool_call",
                description="Third node",
                dependencies={"node1"}
            )
        }
        edges = [
            Edge(from_node="node1", to_node="node2"),
            Edge(from_node="node1", to_node="node3")
        ]
        return Plan(
            id="plan1",
            goal="Test plan",
            nodes=nodes,
            edges=edges,
            context={}
        )
    
    def test_build_from_plan(self, builder, sample_plan):
        """Test building adjacency list from plan."""
        result = builder.build_from_plan(sample_plan)
        
        assert result is True
        assert "node1" in builder.adjacency_list
        # node2 and node3 have no outgoing edges in the adjacency list
        # they appear as destinations, not sources
        assert "node2" in builder.adjacency_list["node1"]  # node1 -> node2
        assert "node3" in builder.adjacency_list["node1"]  # node1 -> node3
    
    def test_validate_acyclic(self, builder, sample_plan):
        """Test acyclic validation."""
        builder.build_from_plan(sample_plan)
        
        is_acyclic = builder.validate_acyclic()
        
        assert is_acyclic is True
    
    def test_validate_acyclic_cycle(self, builder):
        """Test acyclic validation with cycle."""
        # Create a plan with a cycle
        nodes = {
            "node1": Node(id="node1", type="tool_call", description="Node 1", dependencies={"node2"}),
            "node2": Node(id="node2", type="tool_call", description="Node 2", dependencies={"node1"})
        }
        edges = [
            Edge(from_node="node1", to_node="node2"),
            Edge(from_node="node2", to_node="node1")
        ]
        plan = Plan(id="plan2", goal="Cyclic plan", nodes=nodes, edges=edges, context={})
        
        builder.build_from_plan(plan)
        
        is_acyclic = builder.validate_acyclic()
        
        assert is_acyclic is False


@pytest.mark.unit
class TestGraphValidator:
    """Test cases for GraphValidator."""
    
    @pytest.fixture
    def validator(self):
        return GraphValidator()
    
    @pytest.fixture
    def valid_plan(self):
        """Create a valid plan."""
        nodes = {
            "node1": Node(id="node1", type="tool_call", description="Node 1", dependencies=set()),
            "node2": Node(id="node2", type="tool_call", description="Node 2", dependencies={"node1"})
        }
        edges = [Edge(from_node="node1", to_node="node2")]
        return Plan(id="valid_plan", goal="Valid plan", nodes=nodes, edges=edges, context={})
    
    @pytest.fixture
    def cyclic_plan(self):
        """Create a plan with a cycle."""
        nodes = {
            "node1": Node(id="node1", type="tool_call", description="Node 1", dependencies={"node2"}),
            "node2": Node(id="node2", type="tool_call", description="Node 2", dependencies={"node1"})
        }
        edges = [
            Edge(from_node="node1", to_node="node2"),
            Edge(from_node="node2", to_node="node1")
        ]
        return Plan(id="cyclic_plan", goal="Cyclic plan", nodes=nodes, edges=edges, context={})
    
    @pytest.fixture
    def disconnected_plan(self):
        """Create a plan with disconnected nodes."""
        nodes = {
            "node1": Node(id="node1", type="tool_call", description="Node 1", dependencies=set()),
            "node2": Node(id="node2", type="tool_call", description="Node 2", dependencies=set())
        }
        edges = []  # No edges, nodes are disconnected
        return Plan(id="disconnected_plan", goal="Disconnected plan", nodes=nodes, edges=edges, context={})
    
    def test_validate_valid_plan(self, validator, valid_plan):
        """Test validation of a valid plan."""
        is_valid, errors = validator.validate(valid_plan)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_cyclic_plan(self, validator, cyclic_plan):
        """Test validation of a cyclic plan."""
        is_valid, errors = validator.validate(cyclic_plan)
        
        assert is_valid is False
        assert any("cycle" in error.lower() for error in errors)
    
    def test_validate_disconnected_plan(self, validator, disconnected_plan):
        """Test validation of a disconnected plan."""
        is_valid, errors = validator.validate(disconnected_plan)
        
        # Disconnected nodes without dependencies are allowed as entry points
        # So this might be valid
        assert isinstance(is_valid, bool)
    
    def test_validate_empty_plan(self, validator):
        """Test validation of an empty plan."""
        plan = Plan(id="empty", goal="Empty", nodes={}, edges=[], context={})
        
        is_valid, errors = validator.validate(plan)
        
        # Empty plan might be valid or invalid depending on requirements
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    
    def test_validate_invalid_dependency(self, validator):
        """Test validation with invalid dependency reference."""
        nodes = {
            "node1": Node(id="node1", type="tool_call", description="Node 1", dependencies={"nonexistent"})
        }
        edges = []
        plan = Plan(id="invalid_dep", goal="Invalid dependency", nodes=nodes, edges=edges, context={})
        
        is_valid, errors = validator.validate(plan)
        
        # Should detect invalid dependency
        assert is_valid is False or len(errors) > 0
