from django.conf import settings
from django.shortcuts import redirect
from urllib.parse import urlencode
import requests
import json
import datetime
from humanfriendly import format_timespan
from django.http import JsonResponse


def FormErrors(*args):
    """
    Handles form errors that are passed back to AJAX calls
    :param args: A variable number of form instances
    :return: A concatenated string of form errors
    """
    message = ""  # Initialize an empty string to store form errors

    for form_instance in args:
        if form_instance.errors:
            # If the form has errors, concatenate them into the message string
            message += form_instance.errors.as_text()

    return message  # Return the concatenated string of form errors


def reCAPTCHAValidation(token):
    """
    Performs validation of a reCAPTCHA token by making a request to Google's reCAPTCHA API
    :param token: The reCAPTCHA token to be validated
    :return: JSON response from the reCAPTCHA API
    """

    # Make a POST request to the reCAPTCHA API endpoint
    result = requests.post('https://www.google.com/recaptcha/api/siteverify',
                           # Provide data in the request body,
                           # including the reCAPTCHA secret key and the token to be validated
                           data={
                               'secret': settings.RECAPTCHA_PRIVATE_KEY,
                               'response': token
                           })

    # Return the JSON response obtained from the reCAPTCHA API
    return result.json()


def RedirectParams(**kwargs):
    """
    Used to append URL parameters when redirecting users to Google Maps
    :param kwargs: A dictionary of keyword arguments
        - 'url': The base URL to redirect to (e.g., the Google Maps URL)
        - 'params': A dictionary containing additional parameters to append to the URL
    :return: A redirect response with appended parameters
    """
    url = kwargs.get('url')  # Get the base URL from the keyword arguments
    params = kwargs.get('params')  # Get additional parameters from the keyword arguments

    response = redirect(url)  # Create a redirect response with the base URL

    if params:
        # If there are additional parameters, encode them into a query string
        query_string = urlencode(params)
        # Append the query string to the 'Location' header of the response
        response['Location'] += '?' + query_string

    return response  # Return the response with or without appended parameters



class AjaxFormMixin(object):
    """
    Mixin to ajaxify django form - can be overwritten in view
    :param object:
    :return:
    """
    def form_invalid(self, form):
        response = super(AjaxFormMixin, self).form_invalid(form)
        if self.request.is_ajax():
            message = FormErrors(form)
            return JsonResponse({'result': 'Error', 'message': message})
        return response

    def form_valid(self,form):
        response = super(AjaxFormMixin, self).form_valid(form)
        if self.request.is_ajax():
            form.save()
            return JsonResponse({'result': 'Success', 'message': ""})
        return response



def Directions(*args, **kwargs):
    """
    Handles directions from Google Map
    :param args:
    :param kwargs:
    :return:
    """
    origin = f"{kwargs.get('lat_a')}, {kwargs.get('long_a')}"
    destination = f"{kwargs.get('lat_b')}, {kwargs.get('long_b')}"
    waypoints = f"{kwargs.get('lat_c')},{kwargs.get('long_c')}|{kwargs.get('lat_d')}, {kwargs.get('long_d')}"

    result = requests.get('https://maps.googleapis.com/maps/api/directions/json',
                          params={
                              'origin': origin,
                              'destination': destination,
                              'waypoints': waypoints,
                              'key': settings.GOOGLE_API_KEY
                          })

    directions = result.json()
    if directions.get('status') == 'OK':
        routes = directions['routes'][0]['legs']

        total_distance = sum(int(route['distance']['value']) for route in routes)
        total_duration = sum(int(route['duration']['value']) for route in routes)

        route_list = []

        for route in routes:
            route_step = {
                'origin': route['start_address'],
                'destination': route['end_address'],
                'distance': route['distance']['text'],
                'duration': route['duration']['text'],
                'steps': [
                    {
                        'distance': step['distance']['text'],
                        'duration': step['duration']['text'],
                        'instruction': step['html_instructions']
                    }
                    for step in route['steps']
                ]
            }
            route_list.append(route_step)

        return {
            'origin': origin,
            'destination': destination,
            'distance': f"{total_distance / 1000:.2f} Km",
            'duration': format_timespan(total_duration),
            'route': route_list
        }

    return {
        'error': 'Failed to retrieve directions',
    }