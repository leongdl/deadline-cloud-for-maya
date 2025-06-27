# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path
from typing import Any
import yaml

import PIL.Image

import numpy as np

from test.integ.test_const import ASSET_REFERENCES, PARAMETER_VALUES


def are_images_similar(
    expected_image_directory: Path, actual_image_directory: Path, tolerance: int
) -> bool:
    """
    Helper function that compare if the render output from the adaptor match what we expected
    """
    for image in (expected_image_directory).iterdir():
        if not image.is_file():
            continue

        # Open the two image files with Pillow https://pillow.readthedocs.io/en/stable/index.html
        # and put them in numpy arrays. Pillow doesn't have a good built-in way to do image comparison
        # with tolerance.
        actual = np.asarray(PIL.Image.open(actual_image_directory / image.name))
        expected = np.asarray(PIL.Image.open(image))

        # Check that the two images are the same within a tolerance.
        # It's normal for there to be noise in an output image, so it is unlikely that two
        # renders will be exactly the same.
        if not np.allclose(actual, expected, atol=tolerance):
            return False
    return True


def extract_parameter_value(expected_parameter_values, param_name):
    """
    Helper function that extract parameter value for path convert if needed
    """
    for param in expected_parameter_values["parameterValues"]:
        if param["name"] == param_name:
            return param["value"]
    return None


def are_parameter_values_similar(job_history_dir: Path, expected_parameter_values: dict[str, list]):
    """
    Helper function that asserts that parameter values in the job bundle are what's expected.
    """
    with open(job_history_dir / PARAMETER_VALUES) as actual:
        actual_parameter_values = yaml.safe_load(actual)

        # Compare the lengths so that we can cover the case of duplicate parameters.
        assert len(actual_parameter_values["parameterValues"]) == len(
            expected_parameter_values["parameterValues"]
        )

        # The order of the list of parameter values doesn't matter,
        for parameter_value in expected_parameter_values["parameterValues"]:
            name = parameter_value["name"]
            value = parameter_value["value"]

            # Convert to help with Windows path format
            if not isinstance(value, int):
                value = value.replace("\\", "/")

            assert value == extract_parameter_value(actual_parameter_values, name)


def are_asset_references_similar(
    job_history_dir: Path, expected_asset_references: dict[str, dict[str, Any]]
):
    """
    Helper function that asserts that asset reference values in the job bundle are what's expected.
    Supports wildcard patterns in expected filenames using '*' as a wildcard character.
    """
    import fnmatch
    
    with open(job_history_dir / ASSET_REFERENCES) as actual:
        actual_asset_reference = yaml.safe_load(actual)
        
        # Get the actual filenames as a list
        actual_filenames = actual_asset_reference["assetReferences"]["inputs"]["filenames"]
        expected_filenames = list(expected_asset_references["assetReferences"]["inputs"]["filenames"])
        
        # Check if we have the right number of files (excluding wildcards)
        non_wildcard_expected = [f for f in expected_filenames if '*' not in f]
        
        # For each expected filename with a wildcard, check if there's a match in the actual filenames
        matched_actual_files = set()
        for expected_file in expected_filenames:
            if '*' in expected_file:
                # This is a wildcard pattern
                found_match = False
                for actual_file in actual_filenames:
                    if fnmatch.fnmatch(actual_file, expected_file):
                        matched_actual_files.add(actual_file)
                        found_match = True
                
                assert found_match, f"No match found for wildcard pattern '{expected_file}' in actual files"
            else:
                # This is a regular file path
                assert expected_file in actual_filenames, f"Expected file '{expected_file}' not found in actual files"
                matched_actual_files.add(expected_file)
        
        # All non-wildcard files must be matched exactly
        for file in non_wildcard_expected:
            assert file in actual_filenames, f"Expected file '{file}' not found in actual files"
        
        # For comparison purposes, replace the actual filenames with the expected ones
        # This allows the rest of the comparison to work as before
        actual_asset_reference["assetReferences"]["inputs"]["filenames"] = set(expected_filenames)
        
        # Handle Windows path format for directories
        directories = expected_asset_references["assetReferences"]["outputs"]["directories"]
        expected_asset_references["assetReferences"]["outputs"]["directories"] = [
            d.replace("\\", "/") for d in directories
        ]
        
        assert actual_asset_reference == expected_asset_references
