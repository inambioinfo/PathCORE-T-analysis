"""A collection of utility functions (mostly file reading/writing) used
in the PathCORE analysis scripts"""

import os

import pandas as pd


def load_expression_dataset(path_to_file):
    """
    Parameters
    -----------
    path_to_file : str
        The path to the expression dataset.
        Currently expects a tab-delimited file with row and column names,
        where the rows are the genes and the columns are the samples.

    Returns
    -----------
    pandas.DataFrame
    """
    expression_dataset = pd.read_table(path_to_file, header=0)
    index_on = expression_dataset.columns[0]
    expression_dataset.set_index(index_on, inplace=True)
    expression_dataset = expression_dataset[
        -expression_dataset.index.str.contains('?', regex=False)]
    expression_dataset = expression_dataset.sort_index()
    return expression_dataset


def load_pathway_definitions(path_to_file, shorten_pathway_names=None):
    """
    Parameters
    -----------
    path_to_file : str
        The path to the pathway definitions file.
        Currently expects a tab-delimited file with no header and 3 columns:
          pathway, N (number of genes), gene1;gene2;...geneN
    shorten_pathway_names : function(str) (default=None)
        A function that accepts a pathway name (str) and returns the shortened
        pathway name (str). See `shorten_pathway_names.py` in `constants`.

    Returns
    -----------
    dict(str -> set(str)), A dictionary of pathway definitions,
        where a pathway (key) is mapped to a set of genes (value)
    """
    pathway_definitions = pd.read_table(
        path_to_file, header=None,
        names=["pw", "size", "genes"])
    pathway_definitions["genes"] = pathway_definitions["genes"].map(
        lambda x: x.split(";"))
    pathway_definitions.set_index("pw", inplace=True)
    pathway_definitions_map = {}
    for index, row in pathway_definitions.iterrows():
        if shorten_pathway_names:
            index = shorten_pathway_names(index)
        pathway_definitions_map[index] = set(row["genes"])
    return pathway_definitions_map


def load_significant_pathways_file(path_to_file, shorten_pathway_names=None):
    """
    Parameters
    -----------
    path_to_file : str
        The path to the significant pathways file, generated from
        `pathcore_network_from_model_features.py`
        Currently expects a tab-delimited file with a header containing
        columns [feature, side, pathway] at minimum.
    shorten_pathway_names : function(str) (default=None)
        A function that accepts a pathway name (str) and returns the shortened
        pathway name (str). See `shorten_pathway_names.py` in `constants`.

    Returns
    -----------
    pandas.DataFrame
    """
    significant_pathways = pd.read_table(
        path_to_file, header=0, usecols=["feature", "side", "pathway"])
    if shorten_pathway_names:
        significant_pathways["pathway"] = \
            significant_pathways["pathway"].apply(
                lambda x: shorten_pathway_names(x))
    significant_pathways = significant_pathways.sort_values(
        by=["feature", "side"])
    return significant_pathways


def load_weight_matrix(path_to_file, n_features,
                       n_genes=None, path_to_genes_file=None):
    """
    Parameters
    -----------
    path_to_file : str
        The path to the tab-delimited weight matrix file, generated by
        applying a feature construction algorithm to a compendium of
        gene expression data.
        The weight matrix should have shape [n, k] where n is the number of
        genes and k the number of features.
        See `generate_nmf_model.py` for an example. (Additional examples:
        the PCA loadings matrix, ICA unmixing matrix, ADAGE/eADAGE weight
        matrix)
        - Features must contain the full set of genes in the compendium
        - Genes must have been assigned weights that quantify their
          contribution to a given feature
    n_features : int
        The number of features constructed.
    n_genes : int (default=None)
        The number of genes in the compendium. Used to handle the case where
        a weight matrix file contains additional information after the
        weight matrix dataframe (occurs in the eADAGE models used for the
        paper).
    path_to_genes_file : str (default=None)
        A file of gene identifiers, 1 identifier per line. Used to handle the
        case where a weight matrix file does not already specify the gene
        identifiers as row names.

    Returns
    -----------
    pandas.DataFrame
    """
    read_csv_args = {
        "header": None,
        "sep": "\t",
        "index_col": 0 if not path_to_genes_file else None
    }

    if n_genes:
        read_csv_args["nrows"] = n_genes

    weight_matrix = _weight_matrix_file_skip_rows(
        path_to_file, n_features, read_csv_args)

    if path_to_genes_file:
        genes_df = pd.read_csv(
            path_to_genes_file, header=None, names=["genes"])
        weight_matrix = pd.concat([weight_matrix, genes_df], axis=1)
        weight_matrix.set_index("genes", inplace=True)
    else:
        weight_matrix.index.rename("genes", inplace=True)
        weight_matrix.columns = list(range(n_features))
    return weight_matrix


def _weight_matrix_file_skip_rows(path_to_file, n_features, kwargs):
    """Helper function to read the weight matrix file. Used to detect the
    start of the weight matrix file based on the number of features (=> number
    of columns) expected.
    """
    if os.stat(path_to_file).st_size == 0:
        raise ValueError("{0} is empty.".format(path_to_file))
    with open(path_to_file) as file:
        pos = 0
        current_line = file.readline()
        data = current_line.split("\t")
        while len(data) < n_features:
            pos = file.tell()
            current_line = file.readline()
            data = current_line.split("\t")
        file.seek(pos)
        return pd.read_csv(file, **kwargs)