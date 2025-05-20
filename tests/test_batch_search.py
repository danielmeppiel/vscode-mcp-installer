"""Test for the batch search functionality in the registry client."""

import unittest
from unittest.mock import patch, MagicMock

from mcp_installer.registry import MCPRegistryClient


class TestBatchSearchServersFunctionality(unittest.TestCase):
    """Test cases for the batch_search_servers method in MCPRegistryClient."""

    @patch('requests.get')
    def test_batch_search_servers(self, mock_get):
        """Test batch_search_servers method with multiple identifiers."""
        # Mock response for list_servers
        mock_list_response = MagicMock()
        mock_list_response.json.return_value = {
            "servers": [
                {
                    "id": "123",
                    "name": "io.github.glips/figma-context-mcp",
                    "description": "A test server"
                },
                {
                    "id": "456",
                    "name": "io.github.geli2001/datadog-mcp-server",
                    "description": "Another test server"
                },
                {
                    "id": "789",
                    "name": "io.github.mongodb-js/mongodb-mcp-server",
                    "description": "Yet another test server"
                }
            ],
            "metadata": {
                "count": 3
            }
        }
        mock_list_response.raise_for_status.return_value = None
        
        # Mock responses for get_server
        mock_get_responses = {}
        for server_id, name in [
            ("123", "io.github.glips/figma-context-mcp"),
            ("456", "io.github.geli2001/datadog-mcp-server"),
            ("789", "io.github.mongodb-js/mongodb-mcp-server")
        ]:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "id": server_id,
                "name": name,
                "description": f"Server details for {name}",
                "packages": [{"name": f"package-{server_id}"}]
            }
            mock_response.raise_for_status.return_value = None
            mock_get_responses[f"{server_id}"] = mock_response
        
        # Configure mock to return appropriate response for each URL
        def side_effect(url, **kwargs):
            if "/servers/" in url:
                server_id = url.split("/")[-1]
                return mock_get_responses.get(server_id, MagicMock())
            return mock_list_response
        
        mock_get.side_effect = side_effect
        
        # Create client and call batch_search_servers
        client = MCPRegistryClient()
        identifiers = [
            "io.github.glips/figma-context-mcp",
            "io.github.geli2001/datadog-mcp-server",
            "io.github.mongodb-js/mongodb-mcp-server",
            "non-existent-server"  # This one doesn't exist
        ]
        
        result = client.batch_search_servers(identifiers)
        
        # Verify the results
        self.assertEqual(len(result), 4)
        
        # Check that we found the three valid servers
        self.assertIsNotNone(result["io.github.glips/figma-context-mcp"])
        self.assertIsNotNone(result["io.github.geli2001/datadog-mcp-server"])
        self.assertIsNotNone(result["io.github.mongodb-js/mongodb-mcp-server"])
        
        # Check that non-existent server is None
        self.assertIsNone(result["non-existent-server"])
        
        # Check the content of one of the servers
        server_data = result["io.github.glips/figma-context-mcp"]
        self.assertEqual(server_data["id"], "123")
        self.assertEqual(server_data["name"], "io.github.glips/figma-context-mcp")
        self.assertEqual(server_data["packages"][0]["name"], "package-123")
