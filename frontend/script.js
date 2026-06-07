let selectedSkin = "";
let selectedProblems = [];

/* ========================= */
/* NAVIGATION */
/* ========================= */

function scrollToForm() {

    document
        .getElementById("recommendation")
        .scrollIntoView({
            behavior: "smooth"
        });

}

/* ========================= */
/* SKIN TYPE */
/* ========================= */

function selectSkin(element, skin) {

    selectedSkin = skin;

    document
        .querySelectorAll(".skin-card")
        .forEach(card => {
            card.classList.remove("active");
        });

    element.classList.add("active");

}

/* ========================= */
/* SKIN PROBLEM */
/* ========================= */

function toggleProblem(element, problem) {

    element.classList.toggle("active");

    if (selectedProblems.includes(problem)) {

        selectedProblems =
            selectedProblems.filter(
                item => item !== problem
            );

    } else {

        selectedProblems.push(problem);

    }

}

/* ========================= */
/* GET RECOMMENDATION */
/* ========================= */

async function getRecommendation() {

    if (selectedSkin === "") {

        alert("Pilih jenis kulit terlebih dahulu");
        return;

    }

    if (selectedProblems.length === 0) {

        alert("Pilih minimal satu masalah kulit");
        return;

    }

    const button =
        document.querySelector(".btn-recommend");

    button.disabled = true;
    button.innerHTML = "Mencari Rekomendasi...";

    try {

        const response = await fetch(
            "https://porefectly-production.up.railway.app/recommend-all",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    skin_type: selectedSkin,

                    skin_problems: selectedProblems,

                    top_n: 5

                })

            }
        );

        const data = await response.json();

        console.log(data);

        renderResult(data);

        document
            .getElementById("resultSection")
            .scrollIntoView({
                behavior: "smooth"
            });

    }

    catch (error) {

        console.error(error);

        alert(
            "Gagal terhubung ke server rekomendasi."
        );

    }

    finally {

        button.disabled = false;
        button.innerHTML =
            "Dapatkan Rekomendasi";

    }

}

/* ========================= */
/* RENDER RESULT */
/* ========================= */

function renderResult(data) {

    const container =
        document.getElementById(
            "resultContainer"
        );

    container.innerHTML = "";

    let html = `

        <div class="routine-section">

            <h2 class="routine-title">
                Recommended Skincare Products
            </h2>

    `;

    Object.keys(data.results).forEach(type => {

        html += createCategory(
            type,
            data.results[type]
                ?.recommendations || []
        );

    });

    html += `
        </div>
    `;

    container.innerHTML = html;

}

/* ========================= */
/* PRODUCT CATEGORY */
/* ========================= */

function createCategory(type, products) {

    if (products.length === 0)
        return "";

    let html = `

        <div class="category-block">

            <div class="timeline-title">

                ${type}

            </div>

            <div class="product-grid">

    `;

    products.forEach(product => {

        let ingredientsRaw =
            product.ingredients ||
            product.ingridients ||
            "";

        let ingredientsList = "";

        if (ingredientsRaw !== "") {

            ingredientsList =
                `<ul class="ingredient-list">`;

            ingredientsRaw
                .split(",")

                .forEach(item => {

                    ingredientsList +=
                    `
                        <li>
                            ${item.trim()}
                        </li>
                    `;

                });

            ingredientsList +=
                `</ul>`;

        }

        html += `

            <div class="product-card">

                <img
                    src="${getImage(type)}"
                    class="product-image"
                >

                <div class="product-content">

                    <h3>
                        ${product.name}
                    </h3>

                    <p class="brand">
                        ${product.brand}
                    </p>

                    <details>

                        <summary>
                            Ingredients
                        </summary>

                        ${ingredientsList}

                    </details>

                </div>

            </div>

        `;

    });

    html += `

            </div>

        </div>

    `;

    return html;

}

/* ========================= */
/* PRODUCT IMAGE */
/* ========================= */

function getImage(type) {

    const imageMap = {

        "Face Cleanser":
            "images/cleanser.jpg",

        "Toner":
            "images/toner.jpg",

        "Serum":
            "images/serum.jpg",

        "Moisturizer":
            "images/moisturizer.jpg",

        "Sunscreen":
            "images/sunscreen.jpg",

        "Exfoliator":
            "images/exfoliator.jpg",

        "Makeup Remover":
            "images/remover.jpg"

    };

    return imageMap[type] ||
        "images/default.jpg";

}

// FUNGSI BUKA/TUTUP MODAL
function toggleModelModal() {
    const modal = document.getElementById('model-modal');
    if (modal.style.display === 'none' || modal.style.display === '') {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Mencegah scroll body
    } else {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto'; // Mengaktifkan scroll kembali
    }
}

// FUNGSI GANTI TAB (DIPERBAIKI)
function openModelTab(tabId, element) {
    // 1. Sembunyikan semua konten tab
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
    
    // 2. Hapus status active dari semua tombol tab
    document.querySelectorAll('.tab-link').forEach(link => link.classList.remove('active'));
    
    // 3. Tampilkan tab yang dipilih
    document.getElementById(tabId).classList.add('active');
    
    // 4. Set tombol yang diklik menjadi active
    element.classList.add('active');
}

// TUTUP MODAL JIKA KLIK DI AREA GELAP (LUAR KOTAK PUTIH)
document.getElementById('model-modal').addEventListener('click', function(e) {
    if (e.target === this) toggleModelModal();
});