#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from service.core.deepdoc.parser.pdf_parser import RAGFlowPdfParser, PlainParser
from service.core.deepdoc.parser.docx_parser import RAGFlowDocxParser
from service.core.deepdoc.parser.excel_parser import RAGFlowExcelParser
from service.core.deepdoc.parser.txt_parser import RAGFlowTxtParser
from service.core.deepdoc.parser.markdown_parser import RAGFlowMarkdownParser
from service.core.deepdoc.parser.json_parser import RAGFlowJsonParser
from service.core.deepdoc.parser.html_parser import RAGFlowHtmlParser

# Aliases for backward compatibility
PdfParser = RAGFlowPdfParser
DocxParser = RAGFlowDocxParser
ExcelParser = RAGFlowExcelParser
TxtParser = RAGFlowTxtParser
MarkdownParser = RAGFlowMarkdownParser
JsonParser = RAGFlowJsonParser
HtmlParser = RAGFlowHtmlParser

__all__ = [
    "PdfParser",
    "PlainParser",
    "DocxParser",
    "ExcelParser",
    "PptParser",
    "HtmlParser",
    "JsonParser",
    "MarkdownParser",
    "TxtParser",
]