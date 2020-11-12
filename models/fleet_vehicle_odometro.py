# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.osv import expression

class FleetVehiculeOdometer(models.Model):
  _inherit = 'fleet.vehicle.odometer'
  _name = 'fleet.vehicle.odometer'
  _order = 'date desc, value desc'

  company_id = fields.Many2one('res.company', 'Compañia', default=lambda self: self.env.company)
  value = fields.Float('Odometro inicial', digits=(10, 2),
    store=True,
    readonly=False,
    group_operator="min")
  value_final = fields.Float('Odometro final', digits=(10, 2),
    readonly=False,
    store=True,
    group_operator="max")
  total_unidades = fields.Float("Total odometro",
    digits=(10, 2),
    compute="_total_horas",
    group_operator="sum",
    readonly=False,
    store=True)
  date = fields.Date(string='Fecha', default=False)
  work_id = fields.Many2one('fleet.vehicle.work', 'Trabajo',
    domain="[('state','=','activo'),('detalle_ids.vehicle_id','=',vehicle_id),('detalle_ids.inactivo','=',False)]")
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
  odometer_unit = fields.Char(string="unidades horometro")
  able_to_modify_odometer = fields.Boolean(compute='set_access_for_odometer', string='Is user able to modify product?')
  tiene_adjunto = fields.Boolean(compute='_set_adjunto')
  gal = fields.Float(string="Galones")
  liq_id = fields.Many2one('fleet.vehicle.work.liq', 'liquidacion')

  def _set_adjunto(self):
    for reg in self:
      reg.tiene_adjunto = False
      if reg.documentos_ids:
        reg.tiene_adjunto = True



  @api.onchange('vehicle_id')
  def _onchange_vehicle(self):
    for rec in self:
      if rec.vehicle_id:
        rec.odometer_unit = rec.vehicle_id.odometer_unit
        rec.driver_id = rec.vehicle_id.driver_id.id


 # codigo ok adicional colocar force_save="1" en campo

  def set_access_for_odometer(self):
    for record in self:
      record['able_to_modify_odometer'] = False
      if self.env.user.has_group('fleet.fleet_group_manager'):
        record['able_to_modify_odometer'] = True
    #
    # for reg in self:
    #   # reg.able_to_modify_odometer = reg.env['res.users'].has_group('fleet.fleet_group_manager')
    #   reg.able_to_modify_odometer = True

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
    res = {}
    for reg in self:
      if reg.recibo:
        reg.recibo = reg.recibo.upper()
        reg.recibo = " ".join(reg.recibo.split())
        hay_recibo = self.search([
          ('recibo', '=', reg.recibo),
          ('work_id', '=', reg.work_id.id),
        ])
        if hay_recibo:
          warning = {'title': 'Atención:',
                     'message': 'En el sistema hay un recibo interno con el numero %s' % (reg.recibo),
                     'type': 'notification'}
          res.update({'warning': warning})
      return res


  @api.constrains('date')
  def _check_date(self):
    for record in self:
      if not record.date:
        raise ValidationError("Error, Debe dar un valor de fecha")

  @api.constrains('value', 'value_final')
  def _check_value_value_final(self):
    for record in self:
      if record.tipo_odometro == 'odometer':
        if not record.value:
          raise ValidationError("Error, Debe dar un valor odometro inicial")
        if not record.value_final:
          raise ValidationError("Error, Debe dar un valor odometro final")
        if record.value_final < record.value:
          raise ValidationError("Error, El odometro final no puede ser menor que el odometro inicial")
