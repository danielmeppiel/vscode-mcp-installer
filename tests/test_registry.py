#!/usr/bin/env python3.13
"""
Tests for MCP Registry Client functionality
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

from mcp_installer.registry import (
    MCPRegistryClient,
    get_registry_url,
    convert_to_vscode_config
)


class TestRegistryClientFunctions(unittest.TestCase):
    """Test cases for MCP Registry client functions"""

    def test_get_registry_url_default(self):
        """Test that get_registry_url returns the default URL when no env var is set"""
        # Save any existing environment variable
        old_url = os.environ.get('MCP_REGISTRY_URL')
        if old_url:
            del os.environ['MCP_REGISTRY_URL']
            
        try:
            url = get_registry_url()
            self.assertEqual(url, "https://demo.registry.azure-mcp.net")
        finally:
            # Restore any previous env var
            if old_url:
                os.environ['MCP_REGISTRY_URL'] = old_url

    def test_get_registry_url_custom(self):
        """Test that get_registry_url returns the custom URL from environment"""
        # Save any existing environment variable
        old_url = os.environ.get('MCP_REGISTRY_URL')
        
        test_url = "https://test-mcp-registry.example.com"
        os.environ['MCP_REGISTRY_URL'] = test_url
        
        try:
            url = get_registry_url()
            self.assertEqual(url, test_url)
        finally:
            # Restore any previous env var
            if old_url:
                os.environ['MCP_REGISTRY_URL'] = old_url
            else:
                del os.environ['MCP_REGISTRY_URL']


class TestMCPRegistryClient(unittest.TestCase):
    """Test cases for MCPRegistryClient class"""

    @patch('requests.get')
    def test_list_servers(self, mock_get):
        """Test listing servers from the registry"""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "servers": [
                {
                    "id": "123",
                    "name": "Test Server",
                    "description": "A test server"
                }
            ],
            "metadata": {
                "count": 1
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Create client and call list_servers
        client = MCPRegistryClient()
        result = client.list_servers()
        
        # Verify the request
        mock_get.assert_called_once()
        self.assertEqual(result["servers"][0]["name"], "Test Server")

    @patch('requests.get')
    def test_search_servers_with_repo_paths(self, mock_get):
        """Test exact name matching for server search"""
        # Mock response with servers that have repository paths
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "servers": [
                {
                    "id": "123",
                    "name": "io.github.evalstate/mcp-hfspace",
                    "description": "Hugging Face Space MCP server"
                },
                {
                    "id": "124",
                    "name": "github.registry.io/mcp-service",
                    "description": "A server that mentions github in the description"
                },
                {
                    "id": "125",
                    "name": "github",
                    "description": "A server with exact name github"
                },
                {
                    "id": "126",
                    "name": "io.github.felores/github",
                    "description": "Another server with github in the name"
                }
            ],
            "metadata": {
                "count": 4
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Create client and call search_servers
        client = MCPRegistryClient()
        
        # 1. Search for exact name "github" - should match the exact name and description matches
        results = client.search_servers("github")
        
        # Should match:
        # - ID 125 (exact name "github")
        # - ID 124 (has "github" in description)
        # - ID 126 (has "github" in name part and description)
        self.assertEqual(len(results), 3)
        self.assertIn("125", [s["id"] for s in results])
        self.assertIn("124", [s["id"] for s in results])
        self.assertIn("126", [s["id"] for s in results])
        
        # 2. Search for exact name "io.github.felores/github"
        results = client.search_servers("io.github.felores/github")
        
        # Should only match ID 126 (exact name match)
        self.assertEqual(len(results), 1)
        self.assertIn("126", [s["id"] for s in results])
        
        # 3. Search for "hugging" - should match servers with "hugging" in description
        results = client.search_servers("hugging")
        
        # Should match ID 123 (has "hugging" in description)
        self.assertEqual(len(results), 1)
        self.assertIn("123", [s["id"] for s in results])


class TestConfigConversion(unittest.TestCase):
    """Test cases for configuration conversion functions"""

    def test_convert_docker_server(self):
        """Test converting a Docker-based server from registry to VS Code config"""
        # Sample server data from registry
        server_data = {
            "id": "123",
            "name": "org/docker-server",
            "description": "A Docker-based server",
            "packages": [
                {
                    "registry_name": "docker",
                    "name": "mcp/test-server",
                    "version": "1.0.0",
                    "package_arguments": [
                        {
                            "description": "Docker image",
                            "type": "positional",
                            "value": "mcp/test-server:latest"
                        }
                    ],
                    "environment_variables": [
                        {
                            "name": "API_KEY",
                            "description": "API key for authentication"
                        }
                    ]
                }
            ]
        }
        
        # Convert to VS Code config
        vscode_config = convert_to_vscode_config(server_data)
        
        # Verify the config structure
        self.assertEqual(vscode_config["name"], "docker-server")
        self.assertEqual(vscode_config["command"], "docker")
        self.assertIn("run", vscode_config["args"])
        self.assertIn("-i", vscode_config["args"])
        self.assertIn("--rm", vscode_config["args"])
        self.assertIn("-e", vscode_config["args"])
        self.assertIn("API_KEY", vscode_config["args"])
        self.assertIn("mcp/test-server", vscode_config["args"])
        self.assertIn("API_KEY", vscode_config["env"])
    
    def test_convert_docker_with_runtime_arguments(self):
        """Test converting a Docker-based server with runtime_arguments"""
        # Sample server data from registry based on the example provided
        server_data = {
            "id": "de817b95-6a2b-4f3a-9c8a-f9ddb481e07a",
            "name": "io.github.baryhuang/mcp-headless-gmail",
            "description": "A MCP server for Gmail",
            "package_canonical": "docker",
            "packages": [
                {
                    "registry_name": "docker",
                    "name": "mcp-server-headless-gmail",
                    "version": "0.1.0",
                    "runtime_hint": "docker",
                    "runtime_arguments": [
                        {
                            "is_required": True,
                            "format": "string",
                            "value": "run",
                            "default": "run",
                            "type": "positional",
                            "value_hint": "run"
                        },
                        {
                            "is_required": True,
                            "format": "string",
                            "value": "-i",
                            "default": "-i",
                            "type": "positional",
                            "value_hint": "-i"
                        },
                        {
                            "is_required": True,
                            "format": "string",
                            "value": "--rm",
                            "default": "--rm",
                            "type": "positional",
                            "value_hint": "--rm"
                        },
                        {
                            "is_required": True,
                            "format": "string",
                            "value": "buryhuang/mcp-headless-gmail:latest",
                            "default": "buryhuang/mcp-headless-gmail:latest",
                            "type": "positional",
                            "value_hint": "buryhuang/mcp-headless-gmail:latest"
                        }
                    ]
                }
            ]
        }
        
        # Convert to VS Code config
        vscode_config = convert_to_vscode_config(server_data)
        
        # Verify the config structure
        self.assertEqual(vscode_config["name"], "mcp-headless-gmail")
        self.assertEqual(vscode_config["command"], "docker")
        
        expected_args = ["run", "-i", "--rm", "buryhuang/mcp-headless-gmail:latest"]
        self.assertEqual(vscode_config["args"], expected_args)
    
    def test_convert_npm_with_runtime_arguments(self):
        """Test converting an NPM-based server with runtime_arguments"""
        # Sample server data from registry based on the example provided
        server_data = {
            "id": "428785c9-039e-47f6-9636-cbe289cc1990",
            "name": "io.github.azure/azure-mcp",
            "description": "Azure MCP Server",
            "package_canonical": "npm",
            "packages": [
                {
                    "registry_name": "npm",
                    "name": "Azure/azure-mcp",
                    "version": "",
                    "runtime_hint": "npx",
                    "runtime_arguments": [
                        {
                            "is_required": True,
                            "format": "string",
                            "value": "-y",
                            "default": "-y",
                            "type": "positional",
                            "value_hint": "-y"
                        },
                        {
                            "is_required": True,
                            "format": "string",
                            "value": "@azure/mcp@latest",
                            "default": "@azure/mcp@latest",
                            "type": "positional",
                            "value_hint": "@azure/mcp@latest"
                        },
                        {
                            "is_required": True,
                            "format": "string",
                            "value": "server",
                            "default": "server",
                            "type": "positional",
                            "value_hint": "server"
                        },
                        {
                            "is_required": True,
                            "format": "string",
                            "value": "start",
                            "default": "start",
                            "type": "positional",
                            "value_hint": "start"
                        }
                    ]
                }
            ]
        }
        
        # Convert to VS Code config
        vscode_config = convert_to_vscode_config(server_data)
        
        # Verify the config structure
        self.assertEqual(vscode_config["name"], "azure-mcp")
        self.assertEqual(vscode_config["command"], "npx")
        
        expected_args = ["-y", "@azure/mcp@latest", "server", "start"]
        self.assertEqual(vscode_config["args"], expected_args)


if __name__ == "__main__":
    unittest.main()
