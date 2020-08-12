# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta





class MultiImages(models.Model):
    _name = "multi.images2"

    image = fields.Binary('Images')
    description = fields.Char('Description')
    title = fields.Char('title')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehiculo')


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    _name = 'fleet.vehicle'
    _description = 'Vehicle'
    _order = 'license_plate asc, acquisition_date asc'
    cubicaje = fields.Float('Cubicaje en M3')
    carga = fields.Float('Capacidad de carga en Kg')
    multi_images = fields.One2many('multi.images2', 'vehicle_id',
                                   'Multi Imagenes')
    fleet_attach_ids = fields.Many2many('ir.attachment','fleet_vehicle_attachment_rel','vehicle_id','attachment_id', string = 'Documentos Adjuntos')
    description = fields.Text(string='Acerca del vehiculo', translate = True)
    vehicle_type_id = fields.Many2one('vehicle.type', string = 'Tipo Vehiculo')
    color_id = fields.Many2one('vehicle.color', string = 'Color del vehiculo')
    odometer_unit = fields.Selection(selection_add = [('hours', 'Horas')])


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'
    _name = 'fleet.vehicle.log.services'

    name_seq = fields.Char(string='Order Reference',
                           required=True,
                           copy=False,
                           readonly=True,
                           index=True,
                           default=lambda self: _('New'))

    documentos_ids = fields.Many2many('ir.attachment',
                                      'fleet_vehicle_service_attachment_rel',
                                      'service_id', 'attachment_id',
                                      string='Documentos Servicio')

    cost_amount = fields.Float(related='cost_id.amount', string='Costo', store=True, readonly=False)

    # company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    # currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    @api.model
    def create(self, vals):
        if vals.get('name_seq', _('New')) == _('New'):
            vals['name_seq'] = self.env['ir.sequence'].next_by_code('fleet-adicionales.service_log.sequence') or _('New')
        result = super(FleetVehicleLogServices,self).create(vals)
        return(result)

class VehicleType(models.Model):
    """Model Vehicle Type."""

    _name = 'vehicle.type'
    _description = 'Vehicle Type'

    code = fields.Selection([
        ('vehiculo', 'Vehiculo'),
        ('maquinaria', 'Maquinaria Amarilla'),
        ], 'Tipo de maquinaria', default='vehiculo', help='Tipo de maquinaria', required=True)
    
    name = fields.Char(string='Name', required=True,
                       translate=True)
    
class VehicleColor(models.Model):
    """Color Vehicle Type."""

    _name = 'vehicle.color'
    _description = 'Color del vehiculo'
    _order = 'name'
    
    name = fields.Char(string = 'Color', required = True)


# class VehicleWorkfactura(models.Model):
#     """Inicio de labores del trabajo a realizar"""
#     _name = 'vehicle.work.factura'
#     _description = 'Fecha inicial, fecha final, estado del trabajo'
#
#     Name = fields.Char(string = 'Trabajo', required = True)
#     fecha_inicio = fields.Date(string = 'Fecha Inicial', required = True)
#     fecha_final = fields.Date(string = 'Fecha Final', required = True)


# class VehicleWorkDetalle(models.Model):
#     """que parte de la flota se dedicara a realizar un trabajo"""
#     _name = 'vehicle.work.detalle'
#     _description = 'Vehiculos/Maquinaria destinada a un trabajo'
#
#     vehicle_id = fields.Many2one('fleet.vehicle', 'vehiculo a Asignar')
#     fecha_inicio = fields.Date(string = 'Fecha Inicial', required = True)
#     fecha_final = fields.Date(string = 'Fecha Final', required = True)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    state = fields.Selection([('activo', 'Activo'),
                             ('Inactivo','Inactivo'),
                             ('otro', 'Otro')], string="Estado")

    licencia_id = fields.One2many('licencia.res.partner', 'partner_id', String = 'licencias')
    documentos_ids = fields.Many2many('ir.attachment','res_partner_document_rel', 'partner_id', 'attachment_id', string="Documentos adjuntos")
    restriccion = fields.Char(string='Restriccion')
    licencia_cancelada = fields.Boolean(string="Licencia cancelada", default=False)
    fecha_cancelacion = fields.Date(string = "fecha de cancelacion", help="Fecha cancelacion de licencia")
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
    l10n_co_verification_code = fields.Char(compute='_compute_verification_code', string='VC',  # todo remove this field in master
                                            help='Redundancy check to verify the vat number has been typed in correctly.')

    @api.depends('vat')
    def _compute_verification_code(self):
        multiplication_factors = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]

        for partner in self:
            if partner.vat and partner.country_id == self.env.ref('base.co') and len(partner.vat) <= len(multiplication_factors):
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
        if self.sudo().env.ref('base.module_base_vat').state == 'installed':
            # don't check Colombian partners unless they have RUT (= Colombian VAT) set as document type
            self = self.filtered(lambda partner: partner.country_id != self.env.ref('base.co') or\
                                                 partner.l10n_co_document_type == 'rut')
            return super(ResPartner, self).check_vat()
        else:
            return True


class TipoLicenciaResPartner(models.Model):
    _name = 'tipo.licencia.res.partner'
    _description = 'Tipo de Licencia Conduccion tercero'
    name = fields.Char(string = 'Codigo', required = True)
    servicio = fields.Selection([('particular', 'Servicio particular'),
        ('publico', 'Servicio publico')], string='Tipo Servicio',
        help='Indica el tipo de servicio o particular o publico.')
    descripcion = fields.Char(string = 'Descripcion', required = True)

    def name_get(self):
        res = []
        for field in self:
            res.append((field.id, '%s (%s)' % (field.name, field.servicio)))
        return res


class LicenciaResPartner(models.Model):
    _name = 'licencia.res.partner'
    _description = 'Licencia Conduccion tercero'
    _order = 'state asc, fecha_final asc'
    partner_id = fields.Many2one ('res.partner', 'Tercero')
    licencia_id = fields.Many2one('tipo.licencia.res.partner', 'Tipo de licencia')
    restriccion = fields.Char(string = 'Restriccion')
    fecha_inicio = fields.Date(string = 'Fecha Inicial', required = True)
    fecha_final = fields.Date(string = 'Vigencia', required = True)
    state = fields.Selection([
        ('2.active', 'Activo'),
        ('3.diesoon', 'Proxima a vencer'),
        ('4.inactive', 'Inactivo'),
        ('1.cancel', 'Cancelado')
    ], 'Estado licencia', default='2.active', help='Estado de la licencia', required = True)

    @api.model
    def do_enviar_correo(self):
        template_id = self.env.ref('fleet-adicionales.email_template_licence_fleet').id
        template = self.env['mail.template'].browse(template_id)
        template.send_mail(self.id, force_send=True)

    def run_planificador(self):
        """Busca todas las licencias,
        si la fecha de vencimiento es mayor que la fecha actual, pone su estado en inactivo"""

        params = self.env['ir.config_parameter'].sudo()
        delay_alert = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        print('delay_alert', delay_alert)
        date_today = fields.Date.from_string(fields.Date.today())
        print('date_today', date_today)
        outdated_days = fields.Date.to_string(date_today + relativedelta(days=+delay_alert))
        print('outdated_days', outdated_days)

        licencias_proximas_vencer = self.search([('state', '=', '2.active'), ('fecha_final', '<', outdated_days)])
        print('licencias_proximas_vencer', licencias_proximas_vencer)
        licencias_proximas_vencer.write({'state': '3.diesoon'})
        for licencia in licencias_proximas_vencer:
            licencia.do_enviar_correo()

        licencias_vencidas = self.search(
            [('state', 'not in', ['4.inactive', '1.cancel']), ('fecha_final', '<', fields.Date.today())])
        licencias_vencidas.write({'state': '4.inactive'})

        # reg.write({'state': 'inactive'}) if expired.days < 0 :
        #         #             reg.write({'state': 'inactive'})

        # lista = self.search([('state', 'in', ['2.active', '3.diesoon'])]).sudo()
        # params = self.env['ir.config_parameter'].sudo()
        # delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        # for reg in lista:
        #     if reg.fecha_final:
        #         expired = fields.Date.from_string(reg.fecha_final) - fields.Date.from_string(
        #             fields.Date.today(self))
        #         fechafin = fields.Date.from_string(reg.fecha_final)
        #         fechaact = fields.Date.from_string(fields.Date.today())
        #         print('expired.days=', expired.days, ' fechafin =',fechafin, ' fechaact= ', fechaact)
        #         if expired.days < 0 :
        #             reg.write({'state': 'inactive'})
        #         print ('expired.days == delay_alert_contract:',(expired.days == delay_alert_contract))
        #         if expired.days == delay_alert_contract:
        #             if reg.state == '2.active':
        #                 reg.write({'state': '3.diesoon'})
        #             reg.do_enviar_correo()
        return (True)

    @api.model
    def default_get(self, default_fields):
        res = super(LicenciaResPartner, self).default_get(default_fields)
        res.update({
            'fecha_inicio': fields.Date.context_today(self),
            'fecha_final': fields.Date.context_today(self) + relativedelta(years=+1),
            'state': '2.active'
        })
        return res

class FleetVehicleLogContract(models.Model):
    _inherit = 'fleet.vehicle.log.contract'
    _name = 'fleet.vehicle.log.contract'

    documentos_ids = fields.Many2many('ir.attachment',
                                      'fleet_vehicle_contract_attachment_rel',
                                      'contract_id','attachment_id',
                                      string = 'Documentos contrato')
    odometer = fields.Float(string='Odometro contrato',
        help='Digite el odometro al momento del contratar')

    @api.model
    def do_enviar_correo(self):
        template_id = self.env.ref('fleet-adicionales.email_template_vehicle_contract').id
        template = self.env['mail.template'].browse(template_id)
        template.send_mail(self.id, force_send=True)


    @api.model
    def scheduler_manage_contract_expiration(self):
        # This method is called by a cron task
        # It manages the state of a contract, possibly by posting a message on the vehicle concerned and updating its status
        params = self.env['ir.config_parameter'].sudo()
        delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        date_today = fields.Date.from_string(fields.Date.today())
        outdated_days = fields.Date.to_string(date_today + relativedelta(days=+delay_alert_contract))
        nearly_expired_contracts = self.search([('state', '=', 'open'), ('expiration_date', '<', outdated_days)])
        nearly_expired_contracts.write({'state': 'diesoon'})
        for contract in nearly_expired_contracts.filtered(lambda contract: contract.user_id):
            contract.activity_schedule(
                'fleet.mail_act_fleet_contract_to_renew', contract.expiration_date,
                user_id=contract.user_id.id)
            contract.do_enviar_correo()

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




