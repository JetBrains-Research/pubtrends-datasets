import unittest
from typing import List, Dict
from unittest.mock import patch

import numpy as np
from parameterized import parameterized

from src.config.config import Config
from src.db.gse import GSE
from src.semantic_search.semantic_search import SemanticSearcher, stable_deduplicate_gses, get_chunks

GSEs_TO_SEARCH = [
    GSE(
        title="In vivo molecular signatures of severe dengue infection revealed by viscRNA-Seq",
        gse="GSE116672",
        status="Public on Nov 19 2018",
        submission_date="2018-07-05",
        last_update_date="2019-12-31",
        pubmed_id=30530648,
        summary="Dengue virus infection can result in severe symptoms including shock and hemorrhage, but an understanding of the molecular correlates of disease severity is lacking. Bulk transcriptomics on blood samples are difficult to interpret because the blood is composed of different cell types that may react differently to virus infection. Dengue virus RNA can be detected in human plasma, however identifying the cells carrying dengue virus through the bloodstream in vivo has proven challenging. Here we used our recently developed viscRNA-Seq approach to profile transcriptomes of thousands of single blood peripheral mononuclear cells from 6 human subjects with dengue fever and severe dengue, as well as to characterize the cell types associated with dengue virus in the human blood. We found that although no bulk transcriptome marker for severe dengue exists, the expression of MX2 in naive B cells, of CD163 in CD14+/CD16+ monocytes and of other genes in specific cell types is highly predictive for severe dengue. We detected virus-associated cells in the blood of two severe dengue patients with high viral load and discovered the majority of these to be B cells expressing germline IgM or IgD immunoglobulin chains and naive markers but also showing signs of activation and expression of CD69, CXCR4, and other surface receptors. In bystander B cells we detected signs of strong immune activation, parallel hypersomatic evolution and, in one severe degue subject, an anomalously large clone of highly mutated, IgG1 plasmablasts that could be reactive to dengue virus. This study presents a high-resolution molecular exploration into dengue virus infection in humans and can be generalized to any RNA virus.",
        type="Expression profiling by high throughput sequencing",
        contributor="Fabio,,Zanini; Makeda,L,Robinson;  Derek Croote;   Malaya,K,Sahoo; Ana,M,Sanz; Eliana Ortiz-Lasso; Ludwig,L,Albornoz;Fernando,R,Suarez;    Jose,G,Montoya; Leslie Goo; Benjamin,A,Pinsky;  Stephen,R,Quake;    Shirit Einav",
        web_link=None,
        overall_design="Blood cells from dengue virus infected human patients were subjected to virus-inclusive single cell RNA-Seq.",
        repeats=None,
        repeats_sample_list=None,
        variable=None,
        variable_description=None,
        contact="Name: Fabio Zanini;    Email: fabio.zanini@fastmail.fm;    Laboratory: Zanini; Institute: University of New South Wales;   Address: High and Botany St;    City: Kensington;   State: NSW; Zip/postal_code: 2033;  Country: Australia",
        supplementary_file="ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE116nnn/GSE116672/suppl/GSE116672_RAW.tar"
    ),
    GSE(
        title="The major risk factors for Alzheimer's disease: Age, Sex and Genes, modulate the microglia response to Aβ plaques (CDEP)",
        gse="GSE127884",
        status="Public on Apr 23 2019",
        submission_date="2019-03-05",
        last_update_date="2019-04-29",
        pubmed_id=31018141,
        summary="Microglia are involved in Alzheimer's disease (AD) by adopting activated phenotypes. How ageing in the absence or presence of β-amyloid (Aβ) deposition in different brain areas affects this response and whether sex and AD risk genes are involved, remains however largely unknown. Here we analyzed the gene expression profiles of more than 10,000 individual microglia cells isolated from cortex and hippocampus of male and female AppNL-G-F at 4 different stages of Aβ deposition and in age-matched control mice. We demonstrate that microglia adopt two major activated states during normal aging and after exposure to amyloid plaques. One of the responses (activated response microglia, ARM) is enhanced in particular by amyloid plaques and is strongly enriched with AD risk genes. The ARM response is not homogeneous, as subgroups of microglia overexpressing MHC type II and tissue repair genes (Dkk2, Gpnmb, Spp1) are induced upon prolonged Aβ exposure. Microglia in female mice advance faster in the activation trajectories. Similar activated states were also found in a second AD model and in human brain. We demonstrate that abolishing the expression of Apoe, the major genetic risk factor for AD, impairs the establishment of ARMs, while the second microglia response type, enriched for interferon response genes, remains unaffected. Our data indicate that ARMs are the converging point of multiple AD risk factors.",
        type="Expression profiling by high throughput sequencing",
        contributor="Carlo,S,Frigerio;  Leen Wolfs; Nicola Fattorelli;Nicola Thrupp;    Iryna Voytyuk;  Inga Schmidt;   Renzo Mancuso;  Wei-Ting Chen;  Maya Woodbury;  Gyan Srivastava;    Thomas Möller;  Eloise Hudry;   Sudeshna Das;   Takaomi Saido;  Eric Karran;    Bradley Hyman;  V,H,Perry;  Ma",
        web_link=None,
        overall_design="RNA-Seq of cortical and hippocampal microglia in  male APP/PS1-Apoe(null), APP/PS1, C57Bl/6 and C57Bl/6-Apoe(null) mice ;  at month 18",
        repeats=None,
        repeats_sample_list=None,
        variable=None,
        variable_description=None,
        contact="Name: Bart de Strooper;    Email: bart.destrooper@kuleuven.be; Department: VIB-KU Leuven Center for Brain & Disease Research;  Institute: KULeuven;    Address: Campus Gasthuisberg, Herestraat 49, bus 602;   City: Leuven;   Zip/postal_code: 3000;  Country: Belgium",
        supplementary_file="ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE127nnn/GSE127884/suppl/GSE127884_microglia.cdep.SeuratNorm.tsv.gz; ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE127nnn/GSE127884/suppl/GSE127884_microglia.cdep.meta.csv.gz;   ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE127nnn/GSE127884/suppl/GSE127884_microglia.cdep.raw.tsv.gz"
    ),
    GSE(
        title="Stem cell derived human microglia transplanted in mouse brain to study human disease",
        gse="GSE137444",
        status="Public on Oct 16 2019",
        submission_date="2019-09-13",
        last_update_date="2020-01-15",
        pubmed_id=31659342,
        summary="While genetics highlight the role of microglia in Alzheimer's disease (AD), one third of putative AD-risk genes lack adequate mouse orthologs. Here, we successfully engraft human microglia derived from embryonic stem cells in the mouse brain. The cells recapitulate transcriptionally human primary microglia ex vivo and show expression of human specific AD-risk genes. Oligomeric Amyloid-β induces a divergent response in human vs. mouse microglia. This model can be used to study the role of microglia in neurological diseases.",
        type="Expression profiling by high throughput sequencing",
        contributor="Renzo,,Mancuso;    Johanna Van Den Daele;  Nicola Fattorelli;  Leen Wolfs; Sriram Balusu;  Oliver Burton;  Annerieke Sierksma; Yannick Fourne; Suresh Poovathingal;    Amaia Arranz-Mendiguren;    Carlo Sala Frigerio;    Christel Claes; Lutgarde Serneels;  Tom Theys;  Hugh P",
        web_link=None,
        overall_design="To control for variability across different experiments, tissue from three mice was pooled in all experimental conditions, from different litters and transplanted with H9-microglia produced in independent batches of in vitro differentiation. Across the manuscript we report both the number of mice/differentiations pooled, as well as the number of sequencing pools. In summary, 1) we sequenced 2,246 transplanted H9-microglia (n=3/1, 3 mice in 1 combined sequencing pool), 4496 H9-derived monocytes (n=2/1, 2 differentiations in 1 combined sequencing pool) and 3385 microglia in vitro (n=2/1), and 22,846 human primary microglia obtained from cortical surgical resections. 2) We sequenced 4880 transplanted H9-microglia (n=3x2/2) and 9942 host mouse cells (n=3x2/2) and assessed their differential response to oligomeric amyloid beta.",
        repeats=None,
        repeats_sample_list=None,
        variable=None,
        variable_description=None,
        contact="Name: Mark Fiers;  Email: mark.fiers@kuleuven.vib.be;  Department: Center for Brain and Disease;   Institute: VIB; Address: Herestraat 49; City: Leuven;   Zip/postal_code: 3000;  Country: Belgium",
        supplementary_file="ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE137nnn/GSE137444/suppl/GSE137444_chimera_human_h9.tsv.gz;  ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE137nnn/GSE137444/suppl/GSE137444_chimera_mouse.tsv.gz; ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE137nnn/GSE137444/suppl/GSE137444_human_patient.tsv.gz; ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE137nnn/GSE137444/suppl/GSE137444_invitro_mh_mc.tsv.gz"
    ),
]
class TestSemanticSearch(unittest.TestCase):
    def setUp(self):
        self.config = Config(test=True)
        self.semantic_search = SemanticSearcher(self.config)
        self.fetch_texts_embedding = self.enterContext(patch("src.semantic_search.semantic_search.fetch_texts_embedding"))

    @staticmethod
    def _mock_fetch_texts_embedding(texts: List[str], embeddings_if_substring_present: Dict[str, List[float]]):
        embeddings = []
        for text in texts:
            for substring, embedding in embeddings_if_substring_present.items():
                if substring in text.lower():
                    embeddings.append(embedding)
                    break
            else:
                embeddings.append([0.0, 0.0])
        return np.array(embeddings)

    @parameterized.expand([
        # Test case 1: Two duplicate GSEs return the first one
        (
                [GSE(gse="GSE12345", title="Title", last_update_date="2023-01-01"),
                 GSE(gse="GSE12345", title="Title", last_update_date="2023-01-01")],
                [GSE(gse="GSE12345", title="Title", last_update_date="2023-01-01")]
        ),
        # Test case 2: GSE 1, GSE 2, GSE 1. Returns list GSE 1 GSE 2
        (
                [GSE(gse="GSE1", title="Title1", last_update_date="2023-01-01"),
                 GSE(gse="GSE2", title="Title2", last_update_date="2023-01-02"),
                 GSE(gse="GSE1", title="Title1", last_update_date="2023-01-01")],
                [GSE(gse="GSE1", title="Title1", last_update_date="2023-01-01"),
                 GSE(gse="GSE2", title="Title2", last_update_date="2023-01-02")]
        ),
        # Test case 3: GSE 2, GSE 1, GSE 2, GSE 1. Returns list GSE 2 GSE 1
        (
                [GSE(gse="GSE2", title="Title2", last_update_date="2023-01-02"),
                 GSE(gse="GSE1", title="Title1", last_update_date="2023-01-01"),
                 GSE(gse="GSE2", title="Title2", last_update_date="2023-01-02"),
                 GSE(gse="GSE1", title="Title1", last_update_date="2023-01-01")],
                [GSE(gse="GSE2", title="Title2", last_update_date="2023-01-02"),
                 GSE(gse="GSE1", title="Title1", last_update_date="2023-01-01")]
        ),
        # Test case 4: GSE 1, GSE 2, GSE 3. Returns list GSE 1 GSE 2 GSE 3
        (
                [GSE(gse="GSE1", title="Title1", last_update_date="2023-01-01"),
                 GSE(gse="GSE2", title="Title2", last_update_date="2023-01-02"),
                 GSE(gse="GSE3", title="Title3", last_update_date="2023-01-03")],
                [GSE(gse="GSE1", title="Title1", last_update_date="2023-01-01"),
                 GSE(gse="GSE2", title="Title2", last_update_date="2023-01-02"),
                 GSE(gse="GSE3", title="Title3", last_update_date="2023-01-03")]
        ),
    ])
    def test_stable_deduplicate_gses(self, gses: List[GSE], expected_result: List[GSE]):
        result = stable_deduplicate_gses(gses)
        self.assertListEqual(result, expected_result)

    @parameterized.expand([
        ("This is a test sentence.", 10, 2, ["This is a test sentence."]),
        ("This is a test sentence. This is another test sentence. This is a third test sentence.", 13, 1,
         ["This is a test sentence. This is another test sentence.",
          "This is another test sentence. This is a third test sentence."]),
        ("This is a test sentence. This is another test sentence.", 7, 0,
         ["This is a test sentence.", "This is another test sentence."]),
        ("This is a test sentence. This is another test sentence. This is a third test sentence.", 25, 3,
         ["This is a test sentence. This is another test sentence. This is a third test sentence."])
    ])
    def test_get_chunks(self, text: str, max_tokens_per_chunk: int, overlap_sentences: int, expected_result: List[str]):
        result = get_chunks(text, max_tokens_per_chunk, overlap_sentences)
        self.assertListEqual(result, expected_result)

    @parameterized.expand([
        ("mouse brain", {"mouse brain": [1, 1], "alzheimer's": [1, 2]}, [GSEs_TO_SEARCH[2], GSEs_TO_SEARCH[1], GSEs_TO_SEARCH[0]])
    ])
    def test_rank_by_relevance(self, query: str, embeddings_if_word_present: Dict[str, List[float]], expected_result: List[GSE]):
        self.fetch_texts_embedding.side_effect = lambda texts, url: TestSemanticSearch._mock_fetch_texts_embedding(texts, embeddings_if_word_present)
        result = self.semantic_search.rank_by_relevance(GSEs_TO_SEARCH, query)
        # Once for the query and another time for GSEs
        self.assertGreaterEqual(self.fetch_texts_embedding.call_count, 2)
        self.assertListEqual(result, expected_result)
