# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
from odoo.osv import expression



class FleetVehicleLogFuel(models.Model):
    _inherit = 'fleet.vehicle.log.fuel'
    _name = 'fleet.vehicle.log.fuel'
    _order = 'date desc'

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        service = self.env.ref('fleet-adicionales.type_service_refueling', raise_if_not_found=False)
        res.update({
            'date': fields.Date.context_today(self),
            'cost_subtype_id': service and service.id or False,
            'cost_type': 'fuel'
        })
        return res

    liter = fields.Float(string='Galon')
    price_per_liter = fields.Float(string = 'Precio por galon')
    cost_amount = fields.Float(related='cost_id.amount', string='Precio total', store=True, readonly=False)
    documentos_ids = fields.Many2many('ir.attachment',
                                      'fleet_vehicle_services_attachment_rel',
                                      'service_id','attachment_id',
                                      string = 'Documentos servicio')
    calculo = fields.Float(compute='_gasto_combustible', string='Calculo', store= True)

    @api.depends('diferencia', 'liter')
    def _gasto_combustible(self):
      # self.calculo = 0.0
      for reg in self:
        self.calculo = False
        if reg.liter and reg.liter > 0:
          if reg.vehicle_id and reg.vehicle_id.vehicle_type_id and reg.vehicle_id.vehicle_type_id.code == 'vehiculo':
            reg.calculo = round(reg.diferencia/reg.liter, 2)
          else:
            if reg.diferencia and reg.diferencia > 0:
              reg.calculo = round(reg.liter / reg.diferencia, 2)

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
      for rec in self:
        if rec.vehicle_id:
          rec.odometer_unit = rec.vehicle_id.odometer_unit
          rec.purchaser_id = rec.vehicle_id.driver_id.id
          rec.driver_id = rec.vehicle_id.driver_id.id
          registro = rec.env['fleet.vehicle.odometer'].search([
            ('vehicle_id', '=', rec.vehicle_id.id), ('tipo_odometro', '=', 'fuel')],
            order="value_final desc, value desc",
            limit=1)
          rec.odometer = rec.odometer if rec.odometer else (registro.value_final or 0)
          trabajo_det = rec.env['fleet.vehicle.work'].search([
            ('state', '=', 'activo'),
            ('detalle_ids.vehicle_id.id', '=', rec.vehicle_id.id)],
            order="fecha_inicio desc",
            limit=1)
          if trabajo_det:
            rec.work_id = trabajo_det.id
