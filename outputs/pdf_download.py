import io
import json
from datetime import datetime
from typing import Dict, Any, Optional
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Image
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os


class MullionDesignReport:
    """Generate a professional PDF report for mullion design calculations."""
    
    def __init__(self, design_data: Dict[str, Any], project_name: Optional[str] = None):
        """
        Initialize the report generator.
        
        Parameters
        ----------
        design_data : Dict[str, Any]
            Design data dictionary from create_design_json()
        project_name : Optional[str]
            Project name to display in header
        """
        self.data = design_data
        self.project_name = project_name
        self.buffer = io.BytesIO()
        self.page_width = A4[0]
        self.page_height = A4[1]
        # Define margins to match document
        self.left_margin = 30
        self.right_margin = 30
        self.content_width = self.page_width - self.left_margin - self.right_margin
        self.styles = getSampleStyleSheet()
        self._register_fonts()
        self._setup_custom_styles()
    
    def _register_fonts(self):
        """Register custom Raleway fonts."""
        font_dir = "fonts"  # Directory where your font files are stored
        
        # Define font paths - register the weights we'll use
        fonts_to_register = [
            ('Raleway-Regular', 'Raleway-Regular.ttf'),
            ('Raleway-Medium', 'Raleway-Medium.ttf'),
            ('Raleway-SemiBold', 'Raleway-SemiBold.ttf'),
            ('Raleway-Bold', 'Raleway-Bold.ttf'),
            ('Raleway-Italic', 'Raleway-Italic.ttf'),
            ('Raleway-MediumItalic', 'Raleway-MediumItalic.ttf'),
            ('Raleway-SemiBoldItalic', 'Raleway-SemiBoldItalic.ttf'),
            ('Raleway-BoldItalic', 'Raleway-BoldItalic.ttf'),
        ]
        
        # Register each font if the file exists
        for font_name, font_file in fonts_to_register:
            font_path = os.path.join(font_dir, font_file)
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                except Exception as e:
                    print(f"Warning: Could not register font {font_name}: {e}")
            else:
                print(f"Warning: Font file not found: {font_path}")
        
        # Set font variables with fallback to Helvetica if Raleway not available
        self.font_regular = 'Raleway-Regular' if os.path.exists(os.path.join(font_dir, 'Raleway-Regular.ttf')) else 'Helvetica'
        self.font_medium = 'Raleway-Medium' if os.path.exists(os.path.join(font_dir, 'Raleway-Medium.ttf')) else 'Helvetica-Bold'
        self.font_semibold = 'Raleway-SemiBold' if os.path.exists(os.path.join(font_dir, 'Raleway-SemiBold.ttf')) else 'Helvetica-Bold'
        self.font_bold = 'Raleway-Bold' if os.path.exists(os.path.join(font_dir, 'Raleway-Bold.ttf')) else 'Helvetica-Bold'
        self.font_italic = 'Raleway-Italic' if os.path.exists(os.path.join(font_dir, 'Raleway-Italic.ttf')) else 'Helvetica-Oblique'
        
    def _setup_custom_styles(self):
        """Create custom paragraph styles for the report."""
        # Only add styles if they don't already exist
        if 'CustomTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomTitle',
                parent=self.styles['Title'],
                fontSize=18,
                textColor=colors.black,
                spaceAfter=12,
                alignment=TA_CENTER,
                fontName=self.font_bold  # Use Bold for main title
            ))
        
        if 'SectionHeading' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SectionHeading',
                parent=self.styles['Heading1'],
                fontSize=14,
                textColor=colors.HexColor('#db451d'),
                spaceAfter=8,
                spaceBefore=12,
                fontName=self.font_bold,  # Use Bold for section headings
                borderWidth=0,
                borderColor=colors.HexColor('#1f4788'),
                borderPadding=2,
                borderRadius=0,
            ))
        
        if 'SubsectionHeading' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SubsectionHeading',
                parent=self.styles['Heading2'],
                fontSize=11,
                textColor=colors.HexColor('#db451d'),
                spaceAfter=6,
                spaceBefore=8,
                fontName=self.font_semibold  # Use SemiBold for subsection headings
            ))
        
        if 'CustomBodyText' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomBodyText',
                parent=self.styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                fontName=self.font_regular  # Use Regular for body text
            ))
        
        if 'FooterText' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='FooterText',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
                fontName=self.font_regular  # Use Regular for footer
            ))
    
    def _header_footer(self, canvas, doc):
        """Add header and footer to each page."""
        canvas.saveState()
        
        # Header
        canvas.setStrokeColor(colors.grey)
        canvas.setLineWidth(1)
        canvas.line(self.left_margin, self.page_height - 40, 
                   self.page_width - self.right_margin, self.page_height - 40)
        
        canvas.setFont(self.font_semibold, 8)  # Use SemiBold for header
        canvas.setFillColor(colors.grey)
        
        # Header text with optional project name
        if self.project_name:
            header_text = f"{self.project_name}: Mullion Design Calculation Report"
        else:
            header_text = "Mullion Design Calculation Report"
        canvas.drawString(self.left_margin, self.page_height - 32, header_text)
        
        canvas.setFont(self.font_regular, 8)
        canvas.setFillColor(colors.grey)
        date_str = datetime.now().strftime("%B %d, %Y")
        canvas.drawRightString(self.page_width - self.right_margin, self.page_height - 32, date_str)
        
        # Footer
        canvas.setStrokeColor(colors.grey)
        canvas.setLineWidth(1)
        canvas.line(self.left_margin, 40, self.page_width - self.right_margin, 40)
        
        canvas.setFont(self.font_regular, 8)
        canvas.setFillColor(colors.grey)
        
        # Try to add logo, fallback to text if logo not found
        logo_path = "images/TT_Logo_Colour.svg"
        if os.path.exists(logo_path):
            try:
                # For SVG, you might need to convert to PNG/JPG or use a different approach
                # ReportLab has limited SVG support, so this might not work perfectly
                # If SVG doesn't work, consider using PNG/JPG version of logo
                from svglib.svglib import svg2rlg
                from reportlab.graphics import renderPDF
                
                logo = svg2rlg(logo_path)
                if logo:
                    # Scale logo to appropriate size (adjust as needed)
                    scale = 0.15  # Adjust this value to resize logo
                    logo.width *= scale
                    logo.height *= scale
                    logo.scale(scale, scale)
                    renderPDF.draw(logo, canvas, self.left_margin, 22)
                else:
                    canvas.drawString(self.left_margin, 30, "Thornton Tomasetti")
            except:
                # Fallback to text if SVG rendering fails
                canvas.drawString(self.left_margin, 30, "Thornton Tomasetti")
        else:
            canvas.drawString(self.left_margin, 30, "Thornton Tomasetti")
        
        canvas.drawCentredString(self.page_width / 2, 30, f"Page {doc.page}")
        canvas.drawRightString(self.page_width - self.right_margin, 30, 
                              f"Version {self.data['metadata']['version']}")
        
        canvas.restoreState()
    
    def _create_table(self, data, col_widths=None, style_commands=None):
        """Create a formatted table with consistent styling."""
        default_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9e8e0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), self.font_regular),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('LINEABOVE', (0, 0), (-1, 0), 1.0, colors.HexColor('#8b9064')),
            ('LINEBELOW', (0, 0), (-1, 0), 0.7, colors.HexColor('#8b9064')),
            ('LINEBELOW', (0, -1), (-1, -1), 1.0, colors.HexColor('#8b9064')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f4ed')])
        ]
        
        if style_commands:
            default_style.extend(style_commands)
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle(default_style))
        return table
    
    def _add_geometry_section(self, story):
        """Add geometry section to the report."""
        story.append(Paragraph("1. Geometry", self.styles['SectionHeading']))
        
        geom = self.data['geometry']
        data = [
            ['Parameter', 'Value', 'Units'],
            ['Span', f"{geom['span_mm']:.0f}", 'mm'],
            ['Bay Width', f"{geom['bay_width_mm']:.0f}", 'mm'],
            ['Tributary Area', f"{geom['tributary_area_m2']:.3f}", 'm²']
        ]
        
        # Use content width for table
        col_widths = [self.content_width * 0.6, self.content_width * 0.25, self.content_width * 0.15]
        table = self._create_table(data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 12))
    
    def _add_material_section(self, story):
        """Add material properties section to the report."""
        story.append(Paragraph("2. Material Properties", self.styles['SectionHeading']))
        
        mat = self.data['material']
        data = [
            ['Property', 'Value', 'Units'],
            ['Material Type', mat['type'], ''],
            ['Grade', mat['grade'], ''],
            ['Elastic Modulus (E)', f"{mat['elastic_modulus_GPa']:.1f}", 'GPa'],
            ['Yield Strength (fy)', f"{mat['yield_strength_MPa']:.1f}", 'MPa'],
            ['Density', f"{mat['density_kg_m3']:.0f}", 'kg/m³']
        ]
        
        col_widths = [self.content_width * 0.6, self.content_width * 0.25, self.content_width * 0.15]
        table = self._create_table(data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 12))
    
    def _add_loading_section(self, story):
        """Add loading conditions section to the report."""
        story.append(Paragraph("3. Loading Conditions", self.styles['SectionHeading']))
        
        loading = self.data['loading']
        
        story.append(Paragraph("3.1 Wind Loading", self.styles['SubsectionHeading']))
        wind_data = [
            ['Parameter', 'Value', 'Units'],
            ['Include Wind Load', 'Yes' if loading['include_wind'] else 'No', ''],
        ]
        if loading['include_wind']:
            wind_data.extend([
                ['Wind Pressure', f"{loading['wind_pressure_kPa']:.2f}", 'kPa'],
            ])
        
        col_widths = [self.content_width * 0.6, self.content_width * 0.25, self.content_width * 0.15]
        table = self._create_table(wind_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 8))
        
        story.append(Paragraph("3.2 Barrier Loading", self.styles['SubsectionHeading']))
        barrier_data = [
            ['Parameter', 'Value', 'Units'],
            ['Include Barrier Load', 'Yes' if loading['include_barrier'] else 'No', ''],
        ]
        if loading['include_barrier']:
            barrier_data.extend([
                ['Barrier Load', f"{loading['barrier_load_kN_m']:.2f}", 'kN/m'],
                ['Barrier Height', f"{loading['barrier_height_mm']:.0f}", 'mm']
            ])
        
        table = self._create_table(barrier_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 12))
    
    def _add_load_cases_section(self, story):
        """Add load cases section to the report."""
        story.append(Paragraph("4. Load Cases", self.styles['SectionHeading']))
        
        cases = self.data['load_cases']
        
        story.append(Paragraph("4.1 Ultimate Limit State (ULS)", self.styles['SubsectionHeading']))
        uls_data = [['Case Name', 'Wind Factor', 'Barrier Factor']]
        for case in cases['uls_cases']:
            uls_data.append([
                case['name'],
                f"{case['wind_factor']:.2f}",
                f"{case['barrier_factor']:.2f}"
            ])
        
        col_widths = [self.content_width * 0.4, self.content_width * 0.3, self.content_width * 0.3]
        table = self._create_table(uls_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 8))
        
        story.append(Paragraph("4.2 Serviceability Limit State (SLS)", self.styles['SubsectionHeading']))
        sls_data = [['Case Name', 'Wind Factor', 'Barrier Factor']]
        for case in cases['sls_cases']:
            sls_data.append([
                case['name'],
                f"{case['wind_factor']:.2f}",
                f"{case['barrier_factor']:.2f}"
            ])
        
        table = self._create_table(sls_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 12))
    
    def _add_design_criteria_section(self, story):
        """Add design criteria section to the report."""
        story.append(Paragraph("5. Design Criteria", self.styles['SectionHeading']))
        
        criteria = self.data['design_criteria']
        
        story.append(Paragraph("5.1 Deflection Criteria", self.styles['SubsectionHeading']))
        defl = criteria['deflection']
        defl_data = [
            ['Parameter', 'Value', 'Units'],
            ['Criteria Type', defl['criteria_type'], ''],
            ['Deflection Limit', f"{defl['limit_mm']:.2f}", 'mm'],
            ['Limit Ratio', f"span / {defl['limit_ratio']:.0f}", '']
        ]
        
        col_widths = [self.content_width * 0.6, self.content_width * 0.25, self.content_width * 0.15]
        table = self._create_table(defl_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 8))
        
        story.append(Paragraph("5.2 Material Safety", self.styles['SubsectionHeading']))
        safety = criteria['material_safety']
        safety_data = [
            ['Parameter', 'Value', 'Units'],
            ['Safety Factor (γM)', f"{safety['safety_factor']:.2f}", ''],
            ['Allowable Stress', f"{safety['allowable_stress_MPa']:.2f}", 'MPa'],
            ['', f"{safety['allowable_stress_Pa']:.2e}", 'Pa']
        ]
        
        table = self._create_table(safety_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 12))
    
    def _add_uls_results_section(self, story):
        """Add ULS results section to the report."""
        story.append(Paragraph("6. Ultimate Limit State (ULS) Results", self.styles['SectionHeading']))
        
        uls = self.data['uls_results']
        
        story.append(Paragraph("6.1 Governing Values", self.styles['SubsectionHeading']))
        gov_data = [
            ['Parameter', 'Governing Case', 'Value', 'Units'],
            ['Maximum Moment', 
             uls['governing_moment']['case'],
             f"{uls['governing_moment']['value_kNm']:.2f}", 'kNm'],
            ['Maximum Shear',
             uls['governing_shear']['case'],
             f"{uls['governing_shear']['value_kN']:.2f}", 'kN']
        ]
        
        col_widths = [self.content_width * 0.3, self.content_width * 0.3, 
                     self.content_width * 0.2, self.content_width * 0.2]
        table = self._create_table(gov_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 8))
        
        story.append(Paragraph("6.2 All Load Cases", self.styles['SubsectionHeading']))
        cases_data = [['Case', 'RA (kN)', 'RB (kN)', 'M_max (kNm)', 'V_max (kN)']]
        
        for case_name, case_data in uls['reactions'].items():
            cases_data.append([
                case_name,
                f"{case_data['RA_kN']:.2f}",
                f"{case_data['RB_kN']:.2f}",
                f"{case_data['M_max_kNm']:.2f}",
                f"{case_data['V_max_kN']:.2f}"
            ])
        
        col_widths = [self.content_width * 0.25, self.content_width * 0.175, 
                     self.content_width * 0.175, self.content_width * 0.2, self.content_width * 0.2]
        table = self._create_table(cases_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 12))
    
    def _add_sls_results_section(self, story):
        """Add SLS results section to the report."""
        story.append(Paragraph("7. Serviceability Limit State (SLS) Results", self.styles['SectionHeading']))
        
        sls = self.data['sls_results']
        
        story.append(Paragraph("7.1 Governing Values", self.styles['SubsectionHeading']))
        # Use superscript notation that renders correctly
        gov_data = [
            ['Parameter', 'Value', 'Units'],
            ['Deflection Limit', f"{sls['deflection_limit_mm']:.2f}", 'mm'],
            ['Governing Case', sls['governing_case'], ''],
            ['Required I', f"{sls['required_I_cm4']:.2f}", 'cm⁴'],
        ]
        
        col_widths = [self.content_width * 0.6, self.content_width * 0.25, self.content_width * 0.15]
        table = self._create_table(gov_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 8))
        
        story.append(Paragraph("7.2 All Load Cases", self.styles['SubsectionHeading']))
        cases_data = [['Case', 'Required I (cm⁴)', 'Unit Deflection (mm)']]
        
        for case_name, case_data in sls['cases'].items():
            cases_data.append([
                case_name,
                f"{case_data['I_req_cm4']:.2f}",
                f"{case_data['unit_deflection_mm']:.3f}"
            ])
        
        col_widths = [self.content_width * 0.4, self.content_width * 0.3, self.content_width * 0.3]
        table = self._create_table(cases_data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 12))
    
    def _add_design_requirements_section(self, story):
        """Add design requirements summary section."""
        story.append(Paragraph("8. Design Requirements Summary", self.styles['SectionHeading']))
        
        req = self.data['design_requirements']
        
        data = [
            ['Requirement', 'Governing Case', 'Required Value', 'Units'],
            ['Section Modulus (Z)',
             req['section_modulus']['governing_case'],
             f"{req['section_modulus']['required_cm3']:.2f}", 'cm³'],
            ['Moment of Inertia (I)',
             req['moment_of_inertia']['governing_case'],
             f"{req['moment_of_inertia']['required_cm4']:.2f}", 'cm⁴'],
        ]
        
        col_widths = [self.content_width * 0.3, self.content_width * 0.3, 
                     self.content_width * 0.225, self.content_width * 0.175]
        table = self._create_table(data, col_widths=col_widths)
        story.append(table)
        story.append(Spacer(1, 12))
        
        # Add recommendation text
        story.append(Paragraph(
            "<b>Section Selection:</b> Select a mullion section with properties equal to or "
            "exceeding the required values above. Ensure that both the section modulus (Z) "
            "and moment of inertia (I) requirements are satisfied.",
            self.styles['BodyText']
        ))
    
    def generate(self):
        """Generate the complete PDF report."""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=self.right_margin,
            leftMargin=self.left_margin,
            topMargin=60,
            bottomMargin=60
        )
        
        story = []
        
        # Title page
        story.append(Spacer(1, 40))
        story.append(Paragraph("Mullion Design Calculation Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 12))
        
        # Report info
        report_date = datetime.fromisoformat(self.data['metadata']['report_generated'])
        story.append(Paragraph(
            f"<b>Report Generated:</b> {report_date.strftime('%B %d, %Y at %H:%M')}",
            self.styles['BodyText']
        ))
        story.append(Paragraph(
            f"<b>Application:</b> {self.data['metadata']['app_name']} v{self.data['metadata']['version']}",
            self.styles['BodyText']
        ))
        
        if self.project_name:
            story.append(Paragraph(
                f"<b>Project:</b> {self.project_name}",
                self.styles['BodyText']
            ))
        
        story.append(Spacer(1, 24))
        
        # Add all sections
        self._add_geometry_section(story)
        self._add_material_section(story)
        self._add_loading_section(story)
        self._add_load_cases_section(story)
        self._add_design_criteria_section(story)
        self._add_uls_results_section(story)
        self._add_sls_results_section(story)
        self._add_design_requirements_section(story)
        
        # Build PDF
        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        
        self.buffer.seek(0)
        return self.buffer


def create_pdf_report(design_data: Dict[str, Any], project_name: Optional[str] = None) -> io.BytesIO:
    """
    Create a PDF report from design data.
    
    Parameters
    ----------
    design_data : Dict[str, Any]
        Design data dictionary from create_design_json()
    project_name : Optional[str]
        Project name to display in header
    
    Returns
    -------
    io.BytesIO
        Buffer containing the PDF report
    """
    report = MullionDesignReport(design_data, project_name)
    return report.generate()


def add_pdf_download_button(
    design_data: Dict[str, Any],
    filename: str = "mullion_design_report.pdf",
    button_label: str = "📄 Download PDF Report",
    project_name: Optional[str] = None
):
    """
    Add a download button to the Streamlit sidebar for the PDF report.
    
    Parameters
    ----------
    design_data : Dict[str, Any]
        The design data dictionary to export
    filename : str
        The filename for the downloaded PDF file
    button_label : str
        The label for the download button
    project_name : Optional[str]
        Project name to include in header
    """
    pdf_buffer = create_pdf_report(design_data, project_name)
    
    st.sidebar.download_button(
        label=button_label,
        data=pdf_buffer,
        file_name=filename,
        mime="application/pdf",
        help="Download complete design calculation report as PDF"
    )
