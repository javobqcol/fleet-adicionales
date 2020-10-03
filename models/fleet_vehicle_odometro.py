# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression


class FleetVehiculeOdometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'
    _name = 'fleet.vehicle.odometer'
    _order = 'date desc, value desc'


    company_id = fields.Many2one('res.company', 'Compañia', default=lambda self: self.env.company)
    value = fields.Float('Odometro inicial',store=True, readonly=False)
    value_final = fields.Float('Odometro final', readonly=False, store=True)
    total_unidades = fields.Float("Total odometro",compute="_total_horas",group_operator="sum",readonly=False, store=True)
    work_id = fields.Many2one('fleet.vehicle.work', 'Trabajo', domain="[('state', '=', 'activo')]")
    driver_id = fields.Many2one('res.partner', related=None, string="Conductor", required=False)
    es_standby = fields.Boolean(string="Standby", default=False)
    hora_cancelada = fields.Boolean(string="Hora cancelada", default=False)
    tipo_odometro = fields.Char(string='Tipo odometro', default='odometer')
    total_standby = fields.Float("Total standby",compute="_total_horas", group_operator="sum",readonly=False, store=True)
    descripcion = fields.Text(string='Notas',
      placeholder='Cuualquier informacion pertinente respecto a l trabajo realizado')

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
      print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
      for rec in self:
        if rec.vehicle_id:
          print("rec.vehicle_id.odometer_unit==============", rec.vehicle_id.odometer_unit)
          rec.odometer_unit = rec.vehicle_id.odometer_unit
          rec.driver_id = rec.vehicle_id.driver_id.id
          registro = rec.env['fleet.vehicle.odometer'].search([
            ('vehicle_id', '=', rec.vehicle_id.id), ('tipo_odometro', '=', rec.tipo_odometro)],
            order="value_final desc, value desc",
            limit=1)
          rec.value = (registro.value_final or 0)
          trabajo_det = rec.env['fleet.vehicle.work'].search([
            ('state', '=', 'activo'),
            ('detalle_ids.vehicle_id.id', '=', rec.vehicle_id.id)],
            order="fecha_inicio desc",
            limit=1)
          if trabajo_det:
            rec.work_id = trabajo_det.id

    @api.depends('value','value_final')
    def _total_horas(self):
      for record in self:
        record.total_unidades = (record.value_final or 0) - (record.value or 0)
        record.total_unidades = record.total_unidades if record.total_unidades >= 0 else 0
        record.total_standby = record.total_unidades

    @api.model
    def create(self, vals):
      return super().create(vals)
