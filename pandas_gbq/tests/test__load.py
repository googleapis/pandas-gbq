
import numpy
import pandas


def test_encode_chunk_with_unicode():
    """Test that a dataframe containing unicode can be encoded as a file.

    See: https://github.com/pydata/pandas-gbq/issues/106
    """
    from pandas_gbq._load import encode_chunk

    df = pandas.DataFrame(numpy.random.randn(6, 4), index=range(6),
                    columns=list('ABCD'))
    df['s'] = u'信用卡'
    csv_buffer = encode_chunk(df)
    csv_bytes = csv_buffer.read()
    csv_string = csv_bytes.decode('utf-8')
    assert u'信用卡' in csv_string


def test_encode_chunks_splits_dataframe():
    from pandas_gbq._load import encode_chunks
    df = pandas.DataFrame(numpy.random.randn(6, 4), index=range(6))
    num_chunks = len(list(encode_chunks(df, 2)))
    assert num_chunks == 3
