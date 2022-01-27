from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.views import View
from django.conf import settings
from core.forms import CheckoutForm, CouponForm, RefundForm
from core.models import Item, Order, OrderItem, Address, Payment, Coupon, Refund
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest, HttpResponse
import razorpay
import random
import string
# Create your views here.

# authorize razorpay client with API Keys.
razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
#key id=rzp_test_sJVs4d4rEnD6SH
#key secret = jZxWJ2awx7PXIMk4M46uyLqB

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = 'home.html' 

class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(request, 'order_summary.html', context)    
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("/")    
    
class ItemDetailView(DetailView):
    model = Item
    template_name = 'product.html'    

class CheckoutView(View):
    def get(self, request, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)  
            form = CheckoutForm() 
            print(order)
            context = {
                'form':form,
                'order':order,
                'couponform':CouponForm(),
                'DISPLAY_COUPON_FORM':True
                }
            return render(request, "checkout.html", context)    
        except ObjectDoesNotExist:
            messages.info(request, "You do not have an active order")
            return redirect("core:checkout")
        #form
        
    
    def post(self, request, *args, **kwargs):
        #form
        form = CheckoutForm(request.POST, None)
        print(request.POST)
        print(form.errors)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address')
                country = form.cleaned_data.get('country')
                zip = form.cleaned_data.get('zip')
                default = form.cleaned_data.get('default')
                #todo-add functionality for these fields
                #same_shipping_address = form.cleaned_data.get('same_shipping_address')
                #save_info = form.cleaned_data.get('save_info')
                billing_address = Address(
                    user=request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip,
                    default=default
                )       
                billing_address.save()
                order.address = billing_address
                order.save()
                #todo-add redirect to the selected payment option
                return redirect('core:payment')
            messages.warning(request, "Failed to checkout")  
            return redirect('core:checkout') 
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("core:order-summary")    

class PaymentView(View):
    def get(self, request, *args, **kwargs):
        order = Order.objects.get(user=request.user, ordered=False)
        if order.address:
            currency = 'INR'
            amount = order.get_total() * 100  # Rs. 200
            
            # Create a Razorpay Order
            razorpay_order = razorpay_client.order.create(dict(amount=amount,
                                                        currency=currency,
                                                        payment_capture='0'))

            razorpay_order_id = razorpay_order['id']
            callback_url = 'paymenthandler/'     

        # we need to pass these details to frontend.
            context = {}
            context['razorpay_order_id'] = razorpay_order_id
            context['razorpay_merchant_key'] = settings.RAZOR_KEY_ID
            context['razorpay_amount'] = amount
            context['currency'] = currency
            context['callback_url'] = callback_url    

            return render(request, 'payment.html', context)
        else:
            messages.success(request, "You have not added a billing address")
            return redirect('core:checkout')


@csrf_exempt
def paymenthandler(request):
    # only accept POST request.
    if request.method == "POST":
        order = Order.objects.get(user=request.user, ordered=False)
        try:
            # get the required parameters from post request.
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            #razorpay_amount = request.POST.get('razorpay_amount', '')
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
 
            # verify the payment signature.
            result = razorpay_client.utility.verify_payment_signature(
                params_dict)
            if result is None:
                amount = order.get_total() * 100    # Rs. 200
                print(amount)
                try:
 
                    # capture the payemt
                    razorpay_client.payment.capture(payment_id, amount)
 
                    # render success page on successful caputre of payment
                    
                    payment = Payment()
                    payment.razorpay_order_id = razorpay_order_id
                    payment.user = request.user
                    payment.amount = order.get_total()
                    payment.save()

                    order_items = order.items.all()
                    order_items.update(ordered=True)
                    for item in order_items:
                        item.save()

                    order.ordered=True
                    order.payment = payment
                    order.ref_code = create_ref_code()
                    order.save()
                    messages.success(request, "Your order was successful.")
                    return render(request, 'paymentsuccess.html')
                except:
 
                    # if there is an error while capturing payment.
                    return render(request, 'paymentfail.html')
            else:
 
                # if signature verification fails.
                print('Kello')
                return render(request, 'paymentfail.html')
        except:
 
            # if we don't find the required parameters in POST data
            return HttpResponseBadRequest()
    else:
       # if other than POST request is made.
        return HttpResponseBadRequest()   
   

@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
        )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        #check if order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated")
            return redirect('core:order-summary')  
        else:
            order.items.add(order_item)    
            messages.info(request, "This item was added to your cart")
            return redirect('core:product', slug=slug)  
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart")
    return redirect('core:product', slug=slug)           

@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)   


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
                messages.info(request, "This item quantity was updated")
            else:
                order.items.remove(order_item)  
                messages.info(request, "This item was removed from your cart.")  
            messages.info(request, "This item quantity was updated")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug) 

def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        #coupon = get_object_or_404(Coupon, code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")          

class AddCouponView(View):
    def post(self, request, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                coupon = get_coupon(request, code)
                order = Order.objects.get(user=self.request.user, ordered=False)
                order.coupon = coupon
                order.save()
                messages.success(request, "Successfully added coupon")
                return redirect("core:checkout")        
            except ObjectDoesNotExist:
                messages.info(request, "You do not have an active order")
                return redirect("core:checkout")
    

class RequestRefundView(View):
    def get(self, request, *args, **kwargs):
        form = RefundForm()

        context = {
            'form':form,
        }
        return render(request, 'request_refund.html', context)

    def post(self, request, *args, **kwargs):
        form = RefundForm(request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            #edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                #store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()
                messages.info(request, 'Your request was received')
                return redirect('core:request-refund') 
            except ObjectDoesNotExist:
                messages.info(request, 'This order does not exist')
                return redirect('core:request-refund')    


    
  

 
