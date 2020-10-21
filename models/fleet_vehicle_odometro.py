# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

class FleetVehiculeOdometer(models.Model):
  _inherit = 'fleet.vehicle.odometer'
  _name = 'fleet.vehicle.odometer'
  _order = 'date desc, value desc'


  company_id = fields.Many2one('res.company', 'Compañia', default=lambda self: self.env.company)
  value = fields.Float('Odometro inicial', digits=(10, 2), store=True, readonly=False)
  value_final = fields.Float('Odometro final',  digits=(10, 2), readonly=False, store=True,  group_operator="max")
  total_unidades = fields.Float("Total odometro",
    digits=(10, 2),
    compute="_total_horas",
    group_operator="sum",
    readonly=False,
    store=True)
  date = fields.Date(string='Fecha', default=False)
  work_id = fields.Many2one('fleet.vehicle.work', 'Trabajo',
    domain="[('state', '=', 'activo'), ('detalle_ids.vehicle_id', '=', vehicle_id)]")
  driver_id = fields.Many2one('res.partner', related=None, string="Conductor", required=False)
  es_standby = fields.Boolean(string="Standby", default=False)
  hora_cancelada = fields.Boolean(string="Hora cancelada", default=False)
  tipo_odometro = fields.Char(string='Tipo odometro', default='odometer')
  descripcion = fields.Text(string='Notas',
    placeholder='Cualquier información pertinente respecto al trabajo realizado')
  recibo = fields.Char(string='Recibo', help="Numero del recibo de la empresa")
  documentos_ids = fields.Many2many(
    'ir.attachment',
    'fleet_vehicle_odometer_attachment_rel',
    'odometer_id',
    'attachment_id',
    string='Recibos')

  @api.onchange('vehicle_id')
  def _onchange_vehicle(self):
    for rec in self:
      if rec.vehicle_id:
        rec.odometer_unit = rec.vehicle_id.odometer_unit
        rec.driver_id = rec.vehicle_id.driver_id.id
        trabajo_det = rec.env['fleet.vehicle.work'].search([
          ('state', '=', 'activo'),
          ('detalle_ids.vehicle_id.id', '=', rec.vehicle_id.id)],
          order="fecha_inicio desc",
          limit=1)
        if trabajo_det:
          rec.work_id = trabajo_det.id
          work_det = rec.env['fleet.vehicle.work.det'].search([
                       ('work_id', '=', trabajo_det.id),
                       ('vehicle_id', '=', rec.vehicle_id.id)],
                        limit=1)
          if work_det:
            rec.es_standby = work_det.standby
        # return {'domain': {
        #     'work_id': [('detalle_ids.vehicle_id.id', '=', rec.vehicle_id.id), ('state', '=', 'activo')]}}


            # rec.precio_unidad = work_det.precio_unidad
            # rec.unidades_standby = work_det.unidades_standby

  @api.onchange('date')
  def _onchange_date(self):
    for rec in self:
      if rec.date:
        registro = rec.env['fleet.vehicle.odometer'].search([
          ('vehicle_id', '=', rec.vehicle_id.id),
          ('tipo_odometro', '=', rec.tipo_odometro),
          ('date', '<=', rec.date)],
          order="value_final desc, value desc",
          limit=1)
        rec.value = (registro.value_final or 0)

  @api.depends('value', 'value_final', 'total_unidades')
  def _total_horas(self):
    for record in self:
      if record.value_final != 0:
        record.total_unidades = (record.value_final or 0) - (record.value or 0)
      # record.total_standby = record.total_unidades if record.total_unidades >= record.unidades_standby else record.unidades_standby
      # record.valor_unidades = record.total_unidades * record.precio_unidad
      # record.valor_standby = record.total_standby * record.precio_unidad

  @api.onchange('recibo')
  def _onchange_inv_ref(self):
    for reg in self:
      if reg.recibo:
        reg.recibo = reg.recibo.upper()



  @api.constrains('date')
  def _check_date(self):
    for record in self:
      if not record.date:
        raise ValidationError("Error, Debe dar un valor de fecha")

  @api.constrains('value', 'value_final')
  def _check_value_value_final(self):
    for record in self:
      if not record.value:
        raise ValidationError("Error, Debe dar un valor odometro inicial")
      if not record.value_final:
        raise ValidationError("Error, Debe dar un valor odometro final")
      if record.value_final < record.value:
        raise ValidationError("Error, El odometro final no puede ser menor que el odometro inicial")
