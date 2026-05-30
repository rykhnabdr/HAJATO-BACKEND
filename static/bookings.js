const bookingsData = window.bookingsData || [];

function badgeColor(type, value) {

    if (
        value === "confirmed" ||
        value === "paid" ||
        value === "released" ||
        value === "completed"
    ) {
        return "#16a34a";
    }

    if (
        value === "rejected" ||
        value === "refund_required" ||
        value === "refund"
    ) {
        return "#dc2626";
    }

    if (
        value === "waiting_confirmation" ||
        value === "pending_verification" ||
        value === "hold" ||
        value === "waiting_admin_verification"
    ) {
        return "#f59e0b";
    }

    return "#64748b";
}

function statusText(value) {

    if (value === "pending_payment")
        return "Menunggu Pembayaran";

    if (value === "paid")
        return "Sudah Dibayar";

    if (value === "confirmed")
        return "Dikonfirmasi";

    if (value === "completed")
        return "Selesai";

    if (value === "released")
        return "Dana Dicairkan";

    if (value === "hold")
        return "Dana Ditahan";

    if (value === "rejected")
        return "Ditolak";

    return value;
}

function formatRupiah(value) {
    return new Intl.NumberFormat("id-ID").format(value);
}

function formatDate(value) {
    if (!value) return "-";

    const date = new Date(value);

    return date.toLocaleDateString("id-ID", {
        day: "2-digit",
        month: "long",
        year: "numeric"
    });
}

function paymentMethodText(value) {
    if (value === "midtrans") return "Midtrans";
    return value;
}

function openDetail(id) {

    const booking = bookingsData.find(b => b.id === id);

    if (!booking) return;

    document.getElementById("detailContent").innerHTML = `

    <div style="display:grid; gap:14px;">

        <div style="
            background:#1f2937;
            padding:16px;
            border-radius:14px;
        ">
            <h3 style="margin:0 0 8px 0;">
                ${booking.package_name}
            </h3>

            <p style="margin:0; color:#9ca3af;">
                Vendor: ${booking.vendor_name}
            </p>
        </div>

        <div style="
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:12px;
        ">

            <div style="
                background:#1f2937;
                padding:14px;
                border-radius:12px;
            ">
                <small style="color:#9ca3af;">
                    Tanggal
                </small>

                <p style="margin:4px 0 0;">
                    ${formatDate(booking.event_date)}
                </p>
            </div>

            <div style="
                background:#1f2937;
                padding:14px;
                border-radius:12px;
            ">
                <small style="color:#9ca3af;">
                    Jam
                </small>

                <p style="margin:4px 0 0;">
                    ${booking.event_time}
                </p>
            </div>

        </div>

        <div style="
            background:#1f2937;
            padding:14px;
            border-radius:12px;
        ">
            <small style="color:#9ca3af;">
                Lokasi Acara
            </small>

            <p style="margin:4px 0 0;">
                ${booking.location}
            </p>
        </div>

        <div style="
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:12px;
        ">

            <div style="
                background:#1f2937;
                padding:14px;
                border-radius:12px;
            ">
                <small style="color:#9ca3af;">
                    Metode Pembayaran
                </small>

                <p style="margin:4px 0 0;">
                    ${paymentMethodText(booking.payment_method)}
                </p>
            </div>

            <div style="
                background:#1f2937;
                padding:14px;
                border-radius:12px;
            ">
<small style="color:#9ca3af;">
    Status Pembayaran
</small>

<p style="margin:4px 0 0;">
    ${statusText(booking.payment_status)}
</p>
            </div>

        </div>
        <div style="
            background:#064e3b;
            padding:16px;
            border-radius:14px;
        ">
            <small style="color:#a7f3d0;">
                Total Pembayaran
            </small>

            <h2 style="margin:4px 0 0;">
                Rp ${formatRupiah(booking.total_price)}
            </h2>
        </div>

        <div style="
            display:flex;
            gap:10px;
            flex-wrap:wrap;
        ">

            <span style="
                background:${badgeColor('booking', booking.booking_status)};
                padding:8px 12px;
                border-radius:999px;
                font-size:12px;
            ">
                Booking: ${statusText(booking.booking_status)}
            </span>

            <span style="
                background:${badgeColor('payment', booking.payment_status)};
                padding:8px 12px;
                border-radius:999px;
                font-size:12px;
            ">
                Payment: ${statusText(booking.payment_status)}
            </span>

            <span style="
                background:${badgeColor('payout', booking.vendor_payout_status)};
                padding:8px 12px;
                border-radius:999px;
                font-size:12px;
            ">
                Payout: ${statusText(booking.vendor_payout_status)}
            </span>

        </div>

    </div>
    `;

    document.getElementById("detailModal").style.display = "flex";
}

function closeDetail() {
    document.getElementById("detailModal").style.display = "none";
}