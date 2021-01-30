# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
  _inherit = 'res.partner'

  state = fields.Selection([('activo', 'Activo'),
                            ('Inactivo', 'Inactivo'),
                            ('otro', 'Otro')], string="Estado")

  licencia_id = fields.One2many('licencia.res.partner', 'partner_id', String='licencias', ondelete='restrict')
  documentos_ids = fields.Many2many('ir.attachment', 'res_partner_document_rel', 'partner_id', 'attachment_id',
    string="Documentos adjuntos")
  restriccion = fields.Char(string='Restriccion')
  licencia_cancelada = fields.Boolean(string="Licencia cancelada", default=False)
  fecha_cancelacion = fields.Date(string="fecha de cancelacion", help="Fecha cancelacion de licencia")
  motivo = fields.Text(string="Motivo de cancelación", help="digite el motivo por el cual la licencia fue cancelada")
  l10n_co_verification_code = fields.Char(compute='_compute_verification_code', string='VC',
    # todo remove this field in master
    help='Redundancy check to verify the vat number has been typed in correctly.')

  l10n_co_document_type = fields.Selection([('rut', 'NIT'),
                                            ('id_document', 'Cédula'),
                                            ('id_card', 'Tarjeta de Identidad'),
                                            ('passport', 'Pasaporte'),
                                            ('foreign_id_card', 'Cédula Extranjera'),
                                            ('external_id', 'ID del Exterior'),
                                            ('diplomatic_card', 'Carné Diplomatico'),
                                            ('residence_document', 'Salvoconducto de Permanencia'),
                                            ('civil_registration', 'Registro Civil'),
                                            ('national_citizen_id', 'Cédula de ciudadanía')], string='Document Type',
    help='Indicates to what document the information in here belongs to.')
  l10n_co_verification_code = fields.Char(compute='_compute_verification_code', string='VC',
    # todo remove this field in master
    help='Redundancy check to verify the vat number has been typed in correctly.')
  responsable_id = fields.Many2one('res.users', 'Responsable', default=lambda self: self.env.user, index=True)


  @api.depends('vat')
  def _compute_verification_code(self):
    multiplication_factors = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]

    for partner in self:
      if partner.vat and partner.country_id==self.env.ref('base.co') and len(partner.vat) <= len(
        multiplication_factors):
        number = 0
        padded_vat = partner.vat

        while len(padded_vat) < len(multiplication_factors):
          padded_vat = '0' + padded_vat

        # if there is a single non-integer in vat the verification code should be False
        try:
          for index, vat_number in enumerate(padded_vat):
            number += int(vat_number) * multiplication_factors[index]

          number %= 11

          if number < 2:
            partner.l10n_co_verification_code = number
          else:
            partner.l10n_co_verification_code = 11 - number
        except ValueError:
          partner.l10n_co_verification_code = False
      else:
        partner.l10n_co_verification_code = False

    @api.constrains('vat', 'country_id', 'l10n_co_document_type')
    def check_vat(self):
      # check_vat is implemented by base_vat which this localization
      # doesn't directly depend on. It is however automatically
      # installed for Colombia.
      if self.sudo().env.ref('base.module_base_vat').state=='installed':
        # don't check Colombian partners unless they have RUT (= Colombian VAT) set as document type
        self = self.filtered(lambda partner: partner.country_id!=self.env.ref('base.co') or \
                                             partner.l10n_co_document_type=='rut')
        return super(ResPartner, self).check_vat()
      else:
        return True


class TipoLicenciaResPartner(models.Model):
  _name = 'tipo.licencia.res.partner'
  _description = 'Tipo de Licencia Conduccion tercero'
  name = fields.Char(string='Codigo', required=True)
  servicio = fields.Selection([('particular', 'Servicio particular'),
                               ('publico', 'Servicio publico')],
    string='Tipo Servicio',
    help='Indica el tipo de servicio o particular o publico.')
  descripcion = fields.Char(string='Descripcion', required=True)

  def name_get(self):
    res = []
    for field in self:
      res.append((field.id, '%s (%s)' % (field.name, field.servicio)))
    return res


class LicenciaResPartner(models.Model):
  _name = 'licencia.res.partner'
  _description = 'Licencia Conduccion tercero'
  _order = 'fecha_inicio desc'

  name = fields.Text(compute='_compute_licencia_name', store=True)

  partner_id = fields.Many2one('res.partner', 'Tercero', ondelete='restrict')
  licencia_id = fields.Many2one('tipo.licencia.res.partner', 'Tipo de licencia', ondelete='restrict')
  restriccion = fields.Char(string='Restricción licencia')
  fecha_inicio = fields.Date(string='Fecha Inicial', required=True)
  fecha_final = fields.Date(string='Vigencia')
  state = fields.Selection([
    ('active', 'Activo'),
    ('diesoon', 'Proxima a vencer'),
    ('inactive', 'Inactivo'),
    ('cancel', 'Cancelado')
  ], 'Estado licencia', default='active', help='Estado de la licencia', required=True)

  @api.model
  def do_enviar_correo(self, correo, cc_todo):
    template_id = self.env.ref('fleet-adicionales.email_template_licence_fleet').id
    template = self.env['mail.template'].browse(template_id)
    if correo:
      template.email_to = correo
    if cc_todo:
      template.email_cc = cc_todo
    template.send_mail(self.id, force_send=True)

  @api.onchange('fecha_final')
  def _onchange_fecha(self):
    for reg in self:
      if reg.fecha_final and reg.fecha_final < fields.Date.today(): #comparacion x corto circuito
        reg.state = 'inactive'


  def run_planificador(self):
    """Busca todas las licencias,
    si la fecha de vencimiento es mayor que la fecha actual, pone su estado en inactivo"""
    _logger.debug('Ingreso')

    params = self.env['ir.config_parameter'].sudo()
    delay_alert = int(params.get_param('fleet-adicionales.delay_alert_license', default=30))
    correo_hr = params.get_param('fleet-adicionales.resp_hr')
    cc_todo = params.get_param('fleet-adicionales.cc_todo')
    _logger.debug('delay_alert', delay_alert)
    date_today = fields.Date.from_string(fields.Date.today())
    _logger.debug('date_today', date_today)
    outdated_days = fields.Date.to_string(date_today + relativedelta(days=+delay_alert))
    _logger.debug('outdated_days', outdated_days)

    licencias_proximas_vencer = self.search([('state', '=', 'active'), ('fecha_final', '<=', outdated_days)])
    _logger.debug('licencias_proximas_vencer', licencias_proximas_vencer)
    licencias_proximas_vencer.write({'state': 'diesoon'})

    for licencia in licencias_proximas_vencer.filtered(lambda licencia: licencia.partner_id.responsable_id):
      _logger.debug('licencias', licencia.partner_id.name)
      vehiculo = self.env['fleet.vehicle'].search([('driver_id', '=', licencia.partner_id.id)], limit=1)
      _logger.debug(vehiculo.name, '', vehiculo.driver_id.name)
      if vehiculo:
        _logger.debug('tiene vehiculo asignado')
        licencia.do_enviar_correo(correo_hr, cc_todo)
      else:
        _logger.debug('No tiene vehiculo asignado')

    licencias_vencidas = self.search([
      ('state', 'not in', ['inactive', 'cancel']),
      ('fecha_final', '<', outdated_days)])
    licencias_vencidas.write({'state': 'inactive'})

  @api.model
  # def default_get(self, default_fields):
  #   res = super(LicenciaResPartner, self).default_get(default_fields)
  #   # res.update({
  #   #     'fecha_inicio': fields.Date.context_today(self),
  #   #     'fecha_final': fields.Date.context_today(self) + relativedelta(years=+1),
  #   #     'state': 'active',
  #   #     'country_id': country and country.id or False})
  #   res.update({
  #       'fecha_inicio': fields.Date.context_today(self),
  #       'fecha_final': fields.Date.context_today(self) + relativedelta(years=+1),
  #       'state': 'active'})
  #   return res


  @api.depends('partner_id', 'licencia_id', 'fecha_inicio')
  def _compute_licencia_name(self):
    for record in self:
      name = record.partner_id.name
      if record.licencia_id.name:
        name += ' / ' + record.licencia_id.name
      if record.fecha_inicio:
        name += ' / ' + str(record.fecha_inicio)
      record.name = name
