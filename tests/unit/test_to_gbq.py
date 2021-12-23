# Copyright (c) 2021 pandas-gbq Authors All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import google.cloud.bigquery
import google.api_core.exceptions
from pandas import DataFrame
import pytest

from pandas_gbq import gbq
from pandas_gbq.features import FEATURES


@pytest.fixture
def expected_load_method(mock_bigquery_client):
    if FEATURES.pandas_has_parquet_with_lossless_timestamp:
        return mock_bigquery_client.load_table_from_dataframe
    return mock_bigquery_client.load_table_from_file


def test_to_gbq_create_dataset_with_location(mock_bigquery_client):
    mock_bigquery_client.get_table.side_effect = google.api_core.exceptions.NotFound(
        "my_table"
    )
    mock_bigquery_client.get_dataset.side_effect = google.api_core.exceptions.NotFound(
        "my_dataset"
    )
    gbq.to_gbq(
        DataFrame([[1]]), "my_dataset.my_table", project_id="1234", location="us-west1"
    )
    assert mock_bigquery_client.create_dataset.called
    args, _ = mock_bigquery_client.create_dataset.call_args
    sent_dataset = args[0]
    assert sent_dataset.location == "us-west1"


def test_to_gbq_create_dataset_with_if_exists_append(
    mock_bigquery_client, expected_load_method
):
    from google.cloud.bigquery import SchemaField

    mock_bigquery_client.get_table.return_value = google.cloud.bigquery.Table(
        "myproj.my_dataset.my_table",
        schema=(
            SchemaField("col_a", "FLOAT", mode="REQUIRED"),
            SchemaField("col_b", "STRING", mode="REQUIRED"),
        ),
    )
    gbq.to_gbq(
        DataFrame({"col_a": [0.25, 1.5, -1.0], "col_b": ["a", "b", "c"]}),
        "my_dataset.my_table",
        project_id="myproj",
        if_exists="append",
    )
    expected_load_method.assert_called_once()


def test_to_gbq_create_dataset_with_if_exists_append_mismatch(mock_bigquery_client):
    from google.cloud.bigquery import SchemaField

    mock_bigquery_client.get_table.return_value = google.cloud.bigquery.Table(
        "myproj.my_dataset.my_table",
        schema=(SchemaField("col_a", "INTEGER"), SchemaField("col_b", "STRING")),
    )
    with pytest.raises(gbq.InvalidSchema) as exception_block:
        gbq.to_gbq(
            DataFrame({"col_a": [0.25, 1.5, -1.0]}),
            "my_dataset.my_table",
            project_id="myproj",
            if_exists="append",
        )

    exc = exception_block.value
    assert exc.remote_schema == {
        "fields": [
            {"name": "col_a", "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "col_b", "type": "STRING", "mode": "NULLABLE"},
        ]
    }
    assert exc.local_schema == {"fields": [{"name": "col_a", "type": "FLOAT"}]}


def test_to_gbq_create_dataset_with_if_exists_replace(mock_bigquery_client):
    mock_bigquery_client.get_table.side_effect = (
        # Initial check
        google.cloud.bigquery.Table("myproj.my_dataset.my_table"),
        # Recreate check
        google.api_core.exceptions.NotFound("my_table"),
    )
    gbq.to_gbq(
        DataFrame([[1]]),
        "my_dataset.my_table",
        project_id="myproj",
        if_exists="replace",
    )
    # TODO: We can avoid these API calls by using write disposition in the load
    # job. See: https://github.com/googleapis/python-bigquery-pandas/issues/118
    assert mock_bigquery_client.delete_table.called
    assert mock_bigquery_client.create_table.called


def test_to_gbq_create_dataset_translates_exception(mock_bigquery_client):
    mock_bigquery_client.get_table.side_effect = google.api_core.exceptions.NotFound(
        "my_table"
    )
    mock_bigquery_client.get_dataset.side_effect = google.api_core.exceptions.NotFound(
        "my_dataset"
    )
    mock_bigquery_client.create_dataset.side_effect = google.api_core.exceptions.InternalServerError(
        "something went wrong"
    )

    with pytest.raises(gbq.GenericGBQException):
        gbq.to_gbq(DataFrame([[1]]), "my_dataset.my_table", project_id="1234")
