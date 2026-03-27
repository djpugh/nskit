"""Tests for docker_labels utility functions."""

import unittest
from unittest.mock import Mock, patch

from nskit.client.backends.docker_labels import get_recipe_name_from_image, is_nskit_recipe_image


class TestDockerLabels(unittest.TestCase):
    """Tests for Docker label utility functions."""

    @patch("nskit.client.backends.docker_labels.subprocess.run")
    def test_get_recipe_name_from_image(self, mock_run):
        """Extracts recipe name from Docker image labels."""
        mock_run.return_value = Mock(returncode=0, stdout="python_package\n")
        result = get_recipe_name_from_image("myimage:v1")
        self.assertEqual(result, "python_package")

    @patch("nskit.client.backends.docker_labels.subprocess.run")
    def test_get_recipe_name_no_value(self, mock_run):
        """Returns None when label has no value."""
        mock_run.return_value = Mock(returncode=0, stdout="<no value>\n")
        result = get_recipe_name_from_image("myimage:v1")
        self.assertIsNone(result)

    @patch("nskit.client.backends.docker_labels.subprocess.run")
    def test_get_recipe_name_empty(self, mock_run):
        """Returns None when label is empty."""
        mock_run.return_value = Mock(returncode=0, stdout="\n")
        result = get_recipe_name_from_image("myimage:v1")
        self.assertIsNone(result)

    @patch("nskit.client.backends.docker_labels.subprocess.run")
    def test_get_recipe_name_docker_failure(self, mock_run):
        """Returns None when docker inspect fails."""
        mock_run.return_value = Mock(returncode=1, stdout="")
        result = get_recipe_name_from_image("myimage:v1")
        self.assertIsNone(result)

    @patch("nskit.client.backends.docker_labels.subprocess.run")
    def test_get_recipe_name_no_docker(self, mock_run):
        """Returns None when docker is not installed."""
        mock_run.side_effect = FileNotFoundError
        result = get_recipe_name_from_image("myimage:v1")
        self.assertIsNone(result)

    @patch("nskit.client.backends.docker_labels.subprocess.run")
    def test_is_nskit_recipe_image_true(self, mock_run):
        """Returns True for images with nskit.recipe=true label."""
        mock_run.return_value = Mock(returncode=0, stdout="true\n")
        self.assertTrue(is_nskit_recipe_image("myimage:v1"))

    @patch("nskit.client.backends.docker_labels.subprocess.run")
    def test_is_nskit_recipe_image_false(self, mock_run):
        """Returns False for images without nskit label."""
        mock_run.return_value = Mock(returncode=0, stdout="<no value>\n")
        self.assertFalse(is_nskit_recipe_image("myimage:v1"))

    @patch("nskit.client.backends.docker_labels.subprocess.run")
    def test_is_nskit_recipe_image_no_docker(self, mock_run):
        """Returns False when docker is not installed."""
        mock_run.side_effect = FileNotFoundError
        self.assertFalse(is_nskit_recipe_image("myimage:v1"))


if __name__ == "__main__":
    unittest.main()
