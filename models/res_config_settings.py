# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
  _inherit = ['res.config.settings']

  delay_alert_licence = fields.Integer(
      string='Alerta de licencia a vencer',
      default=30,
      config_parameter='fleet-adicionales.delay_alert_license')
  resp_vehicles = fields.Char(
      string='Correo vehiculos',
      help='Correo responsable Vehiculos',
      config_parameter='fleet-adicionales.resp_vehicles')
  resp_hr = fields.Char(
      string='Correo RH',
      help='Correo responsable Recursos Humanos',
      config_parameter='fleet-adicionales.resp_hr')
  resp_contract = fields.Char(
      string='Correo Contratos',
      help='Correo responsable contratos',
      config_parameter='fleet-adicionales.resp_contract')
  cc_todo= fields.Char(
    string='Copias alertas',
    help='Enviar copias de los correos a',
    config_parameter='fleet-adicionales.cc_todo')
