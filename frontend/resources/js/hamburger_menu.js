<!-- Hamburger Menu -->
<div class="hamburger" onclick="toggleMenu()">☰</div>
<div class="menu" id="mainMenu">
  <ul>
    <li><a href="#home">Home</a></li>
    <li><a href="#about">About</a></li>
    <li><a href="#services">Services</a></li>
    <li><a href="#contact">Contact</a></li>
  </ul>
</div>
<script>
  function toggleMenu() {
    var menu = document.getElementById("mainMenu");
    if (menu.classList.contains("show")) {
      menu.classList.remove("show");
    } else {
      menu.classList.add("show");
    }
  }
</script>
