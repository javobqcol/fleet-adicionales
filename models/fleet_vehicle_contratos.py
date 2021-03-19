# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression



class FleetVehicleLogContract(models.Model):
  _inherit = 'fleet.vehicle.log.contract'
  _name = 'fleet.vehicle.log.contract'

  documentos_ids = fields.Many2many(
    'ir.attachment',
    'fleet_vehicle_contract_attachment_rel',
    'contract_id',
    'attachment_id',
    string='Documentos contrato')
  odometer = fields.Float(
    string='Odometro contrato',
    help='Digite el odometro al momento del contratar')

  @api.model
  def do_enviar_correo(self, correo, cc_todo):
    template_id = self.env.ref('fleet-adicionales.email_template_vehicle_contract').id
    template = self.env['mail.template'].browse(template_id)
    if correo:
      template.email_to = correo
    if cc_todo:
      template.email_cc = cc_todo
    template.send_mail(self.id, force_send=True)


  @api.model
  def scheduler_manage_contract_expiration(self):
    # This method is called by a cron task
    # It manages the state of a contract, possibly by posting a message on the vehicle concerned and updating its status
    params = self.env['ir.config_parameter'].sudo()
    delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
    correo_contract = params.get_param('fleet-adicionales.resp_contract')
    cc_todo = params.get_param('fleet-adicionales.cc_todo')
    date_today = fields.Date.from_string(fields.Date.today())
    outdated_days = fields.Date.to_string(date_today + relativedelta(days=+delay_alert_contract))
    nearly_expired_contracts = self.search([('state', '=', 'open'), ('expiration_date', '<', outdated_days)])
    nearly_expired_contracts.write({'state': 'diesoon'})
    for contract in nearly_expired_contracts.filtered(lambda contract: contract.user_id):
      contract.activity_schedule(
          'fleet.mail_act_fleet_contract_to_renew', contract.expiration_date,
          user_id=contract.user_id.id)
      contract.do_enviar_correo(correo_contract, cc_todo)

    expired_contracts = self.search(
        [('state', 'not in', ['expired', 'closed']), ('expiration_date', '<', fields.Date.today())])
    expired_contracts.write({'state': 'expired'})

    futur_contracts = self.search(
        [('state', 'not in', ['futur', 'closed']), ('start_date', '>', fields.Date.today())])
    futur_contracts.write({'state': 'futur'})

    now_running_contracts = self.search([('state', '=', 'futur'), ('start_date', '<=', fields.Date.today())])
    now_running_contracts.write({'state': 'open'})

  def run_scheduler(self):
    self.scheduler_manage_auto_costs()
    self.scheduler_manage_contract_expiration()

  @api.onchange('start_date')
  def _change_start_date(self):
    for reg in self:
      if reg.start_date:
        day = reg.start_date
        next_year =fields.Date.to_string(day+relativedelta(years=+1, days=-1))
        reg.expiration_date = next_year

  @api.onchange('vehicle_id')
  def _onchange_vehicle(self):
    for rec in self:
      if rec.vehicle_id:
        rec.odometer_unit = rec.vehicle_id.odometer_unit
        rec.purchaser_id = rec.vehicle_id.driver_id.id
        trabajo_det = rec.env['fleet.vehicle.work'].search([
          ('state', '=', 'activo'),
          ('detalle_ids.vehicle_id.id', '=', rec.vehicle_id.id)],
          order="fecha_inicio desc",
          limit=1)
        if trabajo_det:
          rec.work_id = trabajo_det.id
