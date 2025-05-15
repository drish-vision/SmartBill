// scripts.js

document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById("salesChart");
    if (ctx) {
        const chart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: JSON.parse(ctx.getAttribute("data-labels")),
                datasets: [{
                    label: "Sales Data",
                    data: JSON.parse(ctx.getAttribute("data-values")),
                    backgroundColor: "rgba(153, 102, 255, 0.6)",
                    borderColor: "rgba(153, 102, 255, 1)",
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
});
