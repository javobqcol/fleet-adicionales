from odoo import models

class FleetVehiclePartsXLS(models.AbstractModel):

  _name = "report.report_partes_monitoreadas_xls"
  _inherit = 'report.report_xlsx.abstract'
  _description = 'reporte de partes monitoreadas'

  def generate_xlsx_report(self, workbook, data, lines):
    sheet = workbook.add_worksheet('Partes')
    indice = 3
    for reg in lines:
      sheet.write(indice, 0, 'Vehiculo / Maquinaria')
      sheet.write(indice, 1, 'Conductor / Operador')
      sheet.write(indice, 2, 'Tipo')
      indice += 1
      sheet.write(indice, 0, reg.name)
      sheet.write(indice, 1, reg.driver_id.display_name)
      sheet.write(indice, 2, reg.vehicle_type_id.name)
      indice += 1
      sheet.write(indice, 1, 'Parte')
      sheet.write(indice, 2, 'Referencia')
      indice += 1
      for record in reg.partes_ids:
        sheet.write(indice, 1, record.template_id.name)
        sheet.write(indice, 2, record.product_id.display_name)
        indice += 1
