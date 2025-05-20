"""Test for the batch resolution functionality in the config module."""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from mcp_installer.config import resolve_servers_from_registry_batch


class TestBatchServerResolution(unittest.TestCase):
    """Test cases for batch server resolution functionality."""

    def test_resolve_servers_from_registry_batch(self):
        """Test resolving multiple servers in batch."""
        # Create a mock registry client
        mock_client = MagicMock()
        
        # Setup the mock to return server details
        server_details = {
            "io.github.glips/figma-context-mcp": {
                "id": "123",
                "name": "io.github.glips/figma-context-mcp",
                "packages": [{"name": "package-123"}]
            },
            "io.github.geli2001/datadog-mcp-server": {
                "id": "456",
                "name": "io.github.geli2001/datadog-mcp-server",
                "packages": [{"name": "package-456"}]
            },
            "io.github.mongodb-js/mongodb-mcp-server": {
                "id": "789",
                "name": "io.github.mongodb-js/mongodb-mcp-server",
                "packages": [{"name": "package-789"}]
            }
        }
        
        mock_client.batch_search_servers.return_value = server_details
        
        # Call the function under test
        server_identifiers = list(server_details.keys())
        result = resolve_servers_from_registry_batch(mock_client, server_identifiers)
        
        # Verify the results
        self.assertEqual(len(result), 3)
        
        # Verify it returned what the client provided
        self.assertEqual(result, server_details)
        
        # Verify the client was called with the right arguments
        mock_client.batch_search_servers.assert_called_once_with(server_identifiers)
    
    def test_resolve_servers_from_registry_batch_with_missing(self):
        """Test resolving servers in batch when some are missing."""
        # Create a mock registry client
        mock_client = MagicMock()
        
        # Setup the mock to return server details with one missing
        server_details = {
            "io.github.glips/figma-context-mcp": {
                "id": "123",
                "name": "io.github.glips/figma-context-mcp",
                "packages": [{"name": "package-123"}]
            },
            "io.github.geli2001/datadog-mcp-server": None,  # This one is missing
            "io.github.mongodb-js/mongodb-mcp-server": {
                "id": "789",
                "name": "io.github.mongodb-js/mongodb-mcp-server",
                "packages": [{"name": "package-789"}]
            }
        }
        
        mock_client.batch_search_servers.return_value = server_details
        
        # Call the function under test and expect an exception
        server_identifiers = list(server_details.keys())
        with self.assertRaises(ValueError) as context:
            resolve_servers_from_registry_batch(mock_client, server_identifiers)
        
        # Verify the error message contains the missing server
        self.assertIn("io.github.geli2001/datadog-mcp-server", str(context.exception))
