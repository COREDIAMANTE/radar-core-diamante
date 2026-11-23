"""Testes locais do classificador de atos; independentes de rede."""
import io
import unittest
import zipfile
import monitorar_aneel as m


class MonitorTest(unittest.TestCase):
    def test_identifica_grupo_e_ativos(self):
        samples = [
            "Diamante Geração de Energia Ltda.",
            "Complexo Termelétrico Jorge Lacerda",
            "CER CTJL n. 478/2025",
            "Itaqui Geração de Energia S.A.",
            "Pecém II Geração de Energia S.A.",
            "UTE Porto do Pecém II",
            "CNPJ 27.093.977/0001-57",
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertTrue(m.direct_match(sample))

    def test_exclui_homonimos(self):
        samples = [
            "Acesso da UTE Jandaia à Subestação Pecém II",
            "Porto do Pecém recebe pás eólicas",
            "Novo empreendimento em Itaqui",
            "Prêmio Diamante de transparência",
            "Revisão geral do ERCAP",
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertFalse(m.direct_match(sample))

    def test_xml_verifica_corpo_e_nao_so_titulo(self):
        xml = b'<article name="DESPACHO N 99"><body>Contrato da Diamante Geracao de Energia Ltda.</body></article>'
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as z:
            z.writestr("ato.xml", xml)
        records = list(m.iter_articles(memory.getvalue()))
        self.assertEqual(len(records), 1)
        self.assertTrue(m.direct_match(records[0][1]))


if __name__ == "__main__":
    unittest.main()
