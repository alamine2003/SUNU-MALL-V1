/* eslint-disable react-refresh/only-export-components */
import { createBrowserRouter, Navigate } from "react-router-dom";
import { lazy } from "react";

import { AuthLayout } from "@/components/layout/AuthLayout";
import { MarketplaceLayout } from "@/components/layout/MarketplaceLayout";
import { CheckoutLayout } from "@/components/layout/CheckoutLayout";
import { MerchantLayout } from "@/components/layout/MerchantLayout";
import { DriverLayout } from "@/components/layout/DriverLayout";
import { AdminLayout } from "@/components/layout/AdminLayout";

const SplashPage = lazy(() => import("@/pages/splash"));
const LoginPage = lazy(() => import("@/pages/login"));
const RegisterClientPage = lazy(() => import("@/pages/register-client"));
const RegisterMerchantPage = lazy(() => import("@/pages/register-merchant"));
const VerifyEmailPage = lazy(() => import("@/pages/verify-email"));
const DriverLoginPage = lazy(() => import("@/pages/driver-login"));

const HomePage = lazy(() => import("@/pages/home"));
const SearchPage = lazy(() => import("@/pages/search"));
const BoutiquesPage = lazy(() => import("@/pages/boutiques"));
const BoutiqueDetailPage = lazy(() => import("@/pages/boutique-detail"));
const ProductDetailPage = lazy(() => import("@/pages/product-detail"));
const CategoryIndexPage = lazy(() => import("@/pages/category"));
const CategoryDetailPage = lazy(() => import("@/pages/category-detail"));
const WishlistPage = lazy(() => import("@/pages/wishlist"));
const RecentlyViewedPage = lazy(() => import("@/pages/recently-viewed"));
const NotificationsPage = lazy(() => import("@/pages/notifications"));

const CartPage = lazy(() => import("@/pages/cart"));
const CheckoutAddressPage = lazy(() => import("@/pages/checkout-address"));
const CheckoutDeliveryPage = lazy(() => import("@/pages/checkout-delivery"));
const CheckoutPaymentPage = lazy(() => import("@/pages/checkout-payment"));
const OrderConfirmedPage = lazy(() => import("@/pages/order-confirmed"));
const OrdersPage = lazy(() => import("@/pages/orders"));
const TrackingPage = lazy(() => import("@/pages/tracking"));
const DeliveryConfirmPage = lazy(() => import("@/pages/delivery-confirm"));

const MerchantDashboardPage = lazy(() => import("@/pages/merchant"));
const CreateShopPage = lazy(() => import("@/pages/create-shop"));
const StoreSettingsPage = lazy(() => import("@/pages/store-settings"));
const AddProductPage = lazy(() => import("@/pages/add-product"));
const CatalogPage = lazy(() => import("@/pages/catalog"));
const SubscriptionsPage = lazy(() => import("@/pages/subscriptions"));
const AnalyticsPage = lazy(() => import("@/pages/analytics"));
const LiveSalesPage = lazy(() => import("@/pages/live-sales"));
const OrderDetailPage = lazy(() => import("@/pages/order-detail"));

const DriverDashboardPage = lazy(() => import("@/pages/driver-dashboard"));
const DriverDeliveryPage = lazy(() => import("@/pages/driver-delivery"));
const DriverProfilePage = lazy(() => import("@/pages/driver-profile"));

const AdminDashboardPage = lazy(() => import("@/pages/admin"));
const AdminUsersPage = lazy(() => import("@/pages/admin-users"));
const AdminManagersPage = lazy(() => import("@/pages/admin-managers"));
const AdminShopsPage = lazy(() => import("@/pages/admin-shops"));
const AdminOrdersPage = lazy(() => import("@/pages/admin-orders"));
const AdminPaymentsPage = lazy(() => import("@/pages/admin-payments"));

export const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/home" replace /> },

  {
    element: <AuthLayout />,
    children: [
      { path: "/splash", element: <SplashPage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register-client", element: <RegisterClientPage /> },
      { path: "/register-merchant", element: <RegisterMerchantPage /> },
      { path: "/verify-email", element: <VerifyEmailPage /> },
      { path: "/driver-login", element: <DriverLoginPage /> },
    ],
  },

  {
    element: <MarketplaceLayout />,
    children: [
      { path: "/home", element: <HomePage /> },
      { path: "/search", element: <SearchPage /> },
      { path: "/boutiques", element: <BoutiquesPage /> },
      { path: "/boutiques/:slug", element: <BoutiqueDetailPage /> },
      { path: "/product/:id", element: <ProductDetailPage /> },
      { path: "/category", element: <CategoryIndexPage /> },
      { path: "/category/:slug", element: <CategoryDetailPage /> },
      { path: "/wishlist", element: <WishlistPage /> },
      { path: "/recently-viewed", element: <RecentlyViewedPage /> },
      { path: "/notifications", element: <NotificationsPage /> },
    ],
  },

  {
    element: <CheckoutLayout />,
    children: [
      { path: "/cart", element: <CartPage /> },
      { path: "/checkout-address", element: <CheckoutAddressPage /> },
      { path: "/checkout-delivery", element: <CheckoutDeliveryPage /> },
      { path: "/checkout-payment", element: <CheckoutPaymentPage /> },
      { path: "/order-confirmed", element: <OrderConfirmedPage /> },
      { path: "/orders", element: <OrdersPage /> },
      { path: "/tracking", element: <TrackingPage /> },
      { path: "/delivery-confirm", element: <DeliveryConfirmPage /> },
    ],
  },

  {
    element: <MerchantLayout />,
    children: [
      { path: "/merchant", element: <MerchantDashboardPage /> },
      { path: "/create-shop", element: <CreateShopPage /> },
      { path: "/store-settings", element: <StoreSettingsPage /> },
      { path: "/add-product", element: <AddProductPage /> },
      { path: "/catalog", element: <CatalogPage /> },
      { path: "/subscriptions", element: <SubscriptionsPage /> },
      { path: "/analytics", element: <AnalyticsPage /> },
      { path: "/live-sales", element: <LiveSalesPage /> },
      { path: "/order-detail", element: <OrderDetailPage /> },
      { path: "/merchant-notifications", element: <NotificationsPage /> },
    ],
  },

  {
    element: <DriverLayout />,
    children: [
      { path: "/driver-dashboard", element: <DriverDashboardPage /> },
      { path: "/driver-delivery", element: <DriverDeliveryPage /> },
      { path: "/driver-profile", element: <DriverProfilePage /> },
      { path: "/driver-notifications", element: <NotificationsPage /> },
    ],
  },

  {
    element: <AdminLayout />,
    children: [
      { path: "/admin", element: <AdminDashboardPage /> },
      { path: "/admin-users", element: <AdminUsersPage /> },
      { path: "/admin-managers", element: <AdminManagersPage /> },
      { path: "/admin-shops", element: <AdminShopsPage /> },
      { path: "/admin-orders", element: <AdminOrdersPage /> },
      { path: "/admin-payments", element: <AdminPaymentsPage /> },
      { path: "/admin-order-detail", element: <OrderDetailPage /> },
      { path: "/admin-notifications", element: <NotificationsPage /> },
    ],
  },

  { path: "*", element: <Navigate to="/home" replace /> },
], { basename: import.meta.env.BASE_URL });
