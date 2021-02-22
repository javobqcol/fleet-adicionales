# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

# cambio 1


class FleetVehicleLogFuel(models.Model):
  _inherit = 'fleet.vehicle.log.fuel'
  _name = 'fleet.vehicle.log.fuel'
  _order = 'date desc'

  @api.model
  def default_get(self, default_fields):
    res = super().default_get(default_fields)
    service = self.env.ref('fleet-adicionales.type_service_refueling', raise_if_not_found=False)
    res.update({
        'date': False,
        'cost_subtype_id': service and service.id or False,
        'cost_type': 'fuel'
    })
    return res

  liter = fields.Float(string='Galon', digits='Volume')
  price_per_liter = fields.Float(string='Precio por galon', digits='Product Price')
  cost_amount = fields.Float(related='cost_id.amount',
    string='Precio total',
    digits='Amount',
    store=True,
    readonly=False)
  documentos_ids = fields.Many2many('ir.attachment',
                                    'fleet_vehicle_fuel_log_attachment_rel',
                                    'service_id', 'attachment_id',
                                    string='Documentos servicio')
  calculo = fields.Float(compute='_gasto_combustible', string='Calculo', store= True)
  currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

  @api.depends('diferencia', 'liter')
  def _gasto_combustible(self):
    # self.calculo = 0.0
    for reg in self:
      self.calculo = False
      if reg.liter and reg.liter > 0:
        if reg.vehicle_id and reg.vehicle_id.vehicle_type_id and reg.vehicle_id.vehicle_type_id.code == 'vehiculo':
          reg.calculo = round(reg.diferencia/reg.liter, 4)
        else:
          if reg.diferencia and reg.diferencia > 0:
            reg.calculo = round(reg.liter / reg.diferencia, 4)

  @api.onchange('liter', 'price_per_liter', 'amount')
  def _onchange_liter_price_amount(self):
    # need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
    # make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
    # liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
    # of 3.0/2=1.5)
    #

    liter = float(self.liter)
    price_per_liter = float(self.price_per_liter)
    amount = float(self.amount)
    if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 4) != amount:
      self.amount = round(liter * price_per_liter, 4)
    elif amount > 0 and liter > 0 and round(amount / liter, 4) != price_per_liter:
      self.price_per_liter = round(amount / liter, 4)
    elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 4) != liter:
      self.liter = round(amount / price_per_liter, 4)

  @api.onchange('inv_ref')
  def _onchange_inv_ref(self):
    res = {}
    for reg in self:
      if reg.inv_ref:
        reg.inv_ref = reg.inv_ref.upper()
        reg.inv_ref = " ".join(reg.inv_ref.split())
        hay_recibo = self.search([
          ('inv_ref', '=', reg.inv_ref),
          ('vendor_id', '=', reg.vendor_id.id),
        ])
        if hay_recibo:
          warning = {'title': 'Atención:',
                     'message': 'En el sistema hay un recibo de combustible para el proveedor %s con el numero %s'
                                % (reg.vendor_id.name or "", reg.inv_ref or "")}
          res.update({'warning': warning})
      return res


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


  @api.constrains('date')
  def _check_date(self):
    for record in self:
      if not record.date:
        raise ValidationError("Error, Debe dar un valor de fecha")



