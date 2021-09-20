# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression
import pytz
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT



class FleetVehicleCost(models.Model):
  _inherit = 'fleet.vehicle.cost'

  driver_id = fields.Many2one('res.partner', string="Conductor")
  cost_subtype_id = fields.Many2one('fleet.service.type', 'Tipo Servicio')
  odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer1', string='Odometro anterior',
    help='Odometro anterior')
  odometer_final = fields.Float(compute='_get_odometer', inverse='_set_odometer2', string='Odometro nuevo',
    help='Odometro nuevo')
  work_id = fields.Many2one('fleet.vehicle.work', 'Trabajo',
    domain="[('state', '=', 'activo'), ('detalle_ids.vehicle_id', '=', vehicle_id)]")
  diferencia = fields.Float(compute='_get_odometer', string='Diferencia')
  amount = fields.Float('Total Price', digits='Amount')
  parent_id = fields.Many2one('fleet.vehicle.cost', 'Parent',
    help='Parent cost to this current cost',
    on_delete='cascade')

  @api.model
  def default_get(self, default_fields):
    res = super().default_get(default_fields)
    res.update({
      'amount': 0.0,
    })
    return res

  def _get_odometer(self):
    self.odometer = 0.0
    self.odometer_final = 0.0
    self.diferencia = 0.0
    for record in self:
      record.diferencia = 0.0
      record.odometer = 0.0
      record.odometer_final = 0.0
      if record.odometer_id:
        record.odometer = record.odometer_id.value
        record.odometer_final = record.odometer_id.value_final
        record.diferencia = record.odometer_id.total_unidades


  # def _set_odometer(self):
  #   for record in self:
  #     if record.odometer_final < record.odometer:
  #       raise UserError(_('Revise el valor del odometro, este no puede ser menor que el valor del tanqueo anterior.'))
  #     if not record.odometer:
  #       raise UserError(_('Emptying the odometer value of a vehicle is not allowed.'))
  #     if record.cost_type == 'contract':
  #       record.odometer_final = record.odometer
  #     if (record.cost_type in ('services') and (record.odometer or 0 != 0.0) and (record.odometer_final or 0) == 0):
  #       record.odometer_final = record.odometer
  #     data = {'value': record.odometer,
  #             'value_final': record.odometer_final,
  #             'total_unidades': ((record.odometer_final or 0) - (record.odometer or 0))
  #               if ((record.odometer_final or 0) - (record.odometer or 0)) >= 0 else False,
  #             'date': record.date or fields.Date.context_today(record),
  #             'vehicle_id': record.vehicle_id.id,
  #             'driver_id': record.driver_id.id,
  #             'tipo_odometro': record.cost_type,
  #             'work_id': record.work_id.id}
  #     temp = self.env['fleet.vehicle.odometer'].browse(record.odometer_id.id)
  #     if (record.odometer_final > 0) and (record.odometer > 0):
  #       if not temp.id:
  #         odo_id = temp.create(data)
  #         self.odometer_id = odo_id
  #       # odo_id tiene el valor del id del registro creado
  #       else:
  #         odo_id = temp.update(data)

  def _set_odometer1(self):
    for record in self:
      if not record.odometer:
        raise UserError(_('Emptying the odometer value of a vehicle is not allowed.'))
      # if record.cost_type == 'contract':
      if record.cost_type in ['contract', 'service']:
        record.odometer_final = record.odometer
      data = {'value': record.odometer,
              'total_unidades': ((record.odometer_final or 0) - (record.odometer or 0))
              if ((record.odometer_final or 0) - (record.odometer or 0)) >= 0 else False,
              'date': record.date or fields.Date.context_today(record),
              'vehicle_id': record.vehicle_id.id,
              'driver_id': record.driver_id.id,
              'tipo_odometro': record.cost_type,
              'work_id': record.work_id.id}
      temp = self.env['fleet.vehicle.odometer'].browse(record.odometer_id.id)
      if record.odometer > 0:
        if not temp.id:
          odo_id = temp.create(data)
          self.odometer_id = odo_id
        # odo_id tiene el valor del id del registro creado
        else:
          odo_id = temp.update(data)

  def _set_odometer2(self):
    for record in self:
      if record.odometer_final < record.odometer:
        raise UserError(_('Revise el valor del odometro, este no puede ser menor que el valor del tanqueo anterior.'))
      # if record.cost_type=='contract':
      if record.cost_type in ['contract', 'service']:
        record.odometer_final = record.odometer
      if record.cost_type in ('services') and (record.odometer_final or 0)==0:
        record.odometer_final = record.odometer
      data = {'value_final': record.odometer_final,
              'total_unidades': ((record.odometer_final or 0) - (record.odometer or 0))
              if ((record.odometer_final or 0) - (record.odometer or 0)) >= 0 else False,
              'date': record.date or fields.Date.context_today(record),
              'vehicle_id': record.vehicle_id.id,
              'driver_id': record.driver_id.id,
              'tipo_odometro': record.cost_type,
              'work_id': record.work_id.id}
      temp = self.env['fleet.vehicle.odometer'].browse(record.odometer_id.id)
      if (record.odometer_final > 0):
        if not temp.id:
          odo_id = temp.create(data)
          self.odometer_id = odo_id
        # odo_id tiene el valor del id del registro creado
        else:
          odo_id = temp.update(data)

  def write(self, vals):
    for reg in self:
      if reg.cost_ids:
        cambios = []
        for costos in reg.cost_ids:
          costos.write({
            'vehicle_id': reg.vehicle_id,
            'work_id': reg.work_id,
            'date' : reg.date,
            'name': reg.name})

    return super(FleetVehicleCost, self).write(vals)

  @api.model_create_multi
  def create(self, vals_list):
    for data in vals_list:
      # make sure that the data are consistent with values of parent and contract records given
      if 'parent_id' in data and data['parent_id']:
        parent = self.browse(data['parent_id'])
        data['vehicle_id'] = parent.vehicle_id.id
        data['date'] = parent.date
        data['cost_type'] = parent.cost_type
        data['work_id'] = parent.work_id.id
      if 'contract_id' in data and data['contract_id']:
        contract = self.env['fleet.vehicle.log.contract'].browse(data['contract_id'])
        data['vehicle_id'] = contract.vehicle_id.id
        data['cost_subtype_id'] = contract.cost_subtype_id.id
        data['cost_type'] = contract.cost_type
      if 'odometer_final' in data and not data['odometer_final']:
        # if received value for odometer is 0, then remove it from the
        # data as it would result to the creation of a
        # odometer log with 0, which is to be avoided
        del data['odometer_final']
      if 'odometer' in data and not data['odometer']:
        # if received value for odometer is 0, then remove it from the
        # data as it would result to the creation of a
        # odometer log with 0, which is to be avoided
        del data['odometer']
      return super().create(vals_list)



  @api.constrains('amount', 'date')
  def _check_date(self):
    for record in self:
      if not record.amount or record.amount == 0.0:
        raise ValidationError("Error, Debe asignar un valor al costo")
      if record.amount < 0.0:
        raise ValidationError("Error, No se pueden asignar costos negativos")
      if not record.date:
        raise ValidationError("Error, Debe dar un valor de fecha")

