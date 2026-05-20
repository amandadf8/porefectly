let selectedSkin = "";

let selectedProblems = [];

/* =========================
   SELECT TIPE KULIT
========================= */

function selectSkin(element, skin){

  selectedSkin = skin;

  document.querySelectorAll(".skin-card")
    .forEach(card => {
      card.classList.remove("active");
    });

  element.classList.add("active");
}

/* =========================
   MULTIPLE SELECT PROBLEM
========================= */

function toggleProblem(element, problem){

  element.classList.toggle("active");

  if(selectedProblems.includes(problem)){

    selectedProblems =
      selectedProblems.filter(
        item => item !== problem
      );

  }else{

    selectedProblems.push(problem);

  }

  console.log(selectedProblems);
}

/* =========================
   FETCH API FASTAPI
========================= */

async function getRecommendation(){

  if(selectedSkin === ""){
    alert("Pilih tipe kulit");
    return;
  }

  if(selectedProblems.length === 0){
    alert("Pilih minimal 1 masalah kulit");
    return;
  }

  try{

    const response = await fetch(
      "http://127.0.0.1:8000/recommend",
      {
        method:"POST",

        headers:{
          "Content-Type":"application/json"
        },

        body:JSON.stringify({

          jenis_kulit: selectedSkin,

          masalah_kulit: selectedProblems

        })

      }
    );

    const data = await response.json();

    console.log(data);

    const resultContainer =
      document.getElementById("resultContainer");

    resultContainer.innerHTML = "";

    data.rekomendasi.forEach(item => {

      resultContainer.innerHTML += `

        <div class="card">

          <img src="https://images.unsplash.com/photo-1556228578-8c89e6adf883?q=80&w=800">

          <h3>${item.nama_produk}</h3>

          <p><b>Brand:</b> ${item.brand}</p>

          <p><b>Rating:</b> ⭐ ${item.rating}</p>

          <p class="price">
            Rp ${item.harga}
          </p>

        </div>

      `;

    });

  }catch(error){

    console.log(error);

    alert("Terjadi error saat mengambil data");

  }

}