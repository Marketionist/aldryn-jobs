# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse, resolve, Resolver404
from django.utils.translation import (
    ugettext_lazy as _,
    get_language_from_request
)

from aldryn_jobs.models import JobOffer
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool


def get_joboffer_from_path(path, language, current_url=None):
    # There is an issue with resolve(path) which is related to django cache
    # (django functools memoize) which uses usual dict and cannot be disabled
    # that leads to a Resolver404 because that cache contains wrong language
    # url resolver. Since request at the moment of calling this function
    # already contains resolver with desired result - we will try to use that
    # In best case this block of code (current_url is None) won't be
    # executed, but if it is - we'll try to get this resolved or will fail
    # with pointing to this place and catch traceback, THE REAL one.
    if current_url is None:
        try:
            current_url = resolve(path)
        except Resolver404:
            raise ImproperlyConfigured(
                "Could not resolve path to obtain current url for"
                " populating cms menu")

    if current_url.url_name == 'job-offer-detail':
        job_offer = JobOffer.objects.language(language)

        if 'category_slug' in current_url.kwargs:
            category_slug = current_url.kwargs['category_slug']
            job_offer = job_offer.filter(
                category__translations__slug=category_slug,
                category__translations__language_code=language
            )

        if 'job_offer_slug' in current_url.kwargs:
            job_slug = current_url.kwargs['job_offer_slug']
            # FIXME: is there is a reason for explicit language 'en'?
            job_offer = job_offer.translated('en', slug=job_slug)

        if job_offer.count():
            # Let MultipleObjectsReturned propagate if it is raised
            return job_offer.get()

    return None


@toolbar_pool.register
class JobsToolbar(CMSToolbar):

    def populate(self):
        def can(actions, model):
            if isinstance(actions, basestring):
                actions = [actions]
            for action in actions:
                perm = 'aldryn_jobs.%(action)s_%(model)s' % {
                    'action': action, 'model': model
                }
                if not self.request.user.has_perm(perm):
                    return False
            return True

        if self.is_current_app and (can(['add', 'change'], 'joboffer') or
                                    can(['add', 'change'], 'jobsconfig')):
            menu = self.toolbar.get_or_create_menu('jobs-app', _('Jobs'))
            if can(['add', 'change'], 'joboffer'):
                menu.add_modal_item(
                    _('Add Job Offer'),
                    reverse('admin:aldryn_jobs_joboffer_add')
                )
                language = get_language_from_request(
                    self.request, check_path=True
                )
                # try to reuse resolver_match instead of doing double work with
                # cache issues, see comments inside of get_joboffer_from_path
                current_url = getattr(self.request, 'resolver_match', None)
                job_offer = get_joboffer_from_path(
                    self.request.path, language, current_url=current_url
                )
                if job_offer:
                    url = reverse(
                        'admin:aldryn_jobs_joboffer_change',
                        args=(job_offer.pk,)
                    )
                    menu.add_modal_item(_('Edit Job Offer'), url, active=True)

            if can(['add', 'change'], 'jobsconfig'):
                url = reverse('admin:aldryn_jobs_jobsconfig_changelist')
                menu.add_sideframe_item(_('Configure Jobs Application'), url)
