async function loadTars() {
  const loader = document.getElementById("loader");
  const tree = document.getElementById("tree");
  loader.classList.add("open");

  try {
    const resp = await fetch(`tarinfo`);
    const data = await resp.json();
    tree.appendChild(renderTree(data));
    attachFolderHandlers();
  } catch (error) {
    tree.textContent = "Data loading error";
  } finally {
    loader.classList.remove("open");
  }
}

function createProgressContainer(parentContainer) {
  const progressContainer = document.createElement("span");
  progressContainer.className = "progress-container";
  parentContainer.appendChild(progressContainer);

  const spinnerContainer = document.createElement("span");
  spinnerContainer.className = "spinner-inline";
  progressContainer.appendChild(spinnerContainer);

  const percentContainer = document.createElement("span");
  percentContainer.className = "percent";
  percentContainer.innerText = `🔐 Decryption...`;
  progressContainer.appendChild(percentContainer);

  return progressContainer;
}

async function download(clicked) {
  let foundRoot = undefined;
  let foundBackup = undefined;
  let foundEncrypted = undefined;
  let parentRow = document.querySelector(
    `[data-id='${clicked.file_meta._parent}']`
  );
  while (!foundRoot || !foundBackup) {
    if (!foundRoot) {
      if (parentRow.classList.contains("root")) {
        foundRoot = parentRow;
      }
    }
    if (!foundBackup) {
      if (parentRow.classList.contains("backup")) {
        foundBackup = parentRow;
      }
    }
    if (!foundEncrypted) {
      if (parentRow.classList.contains("encrypted")) {
        foundEncrypted = parentRow;
      }
    }
    parentRow = document.querySelector(
      `[data-id='${parentRow.file_meta._parent}']`
    );
  }

  const rootFolder = foundRoot.file_meta.name;
  const backupFile = foundBackup.file_meta.name;
  let archive = rootFolder + "/" + backupFile;
  let file_size = clicked.file_meta.size;
  //let encrypted = clicked.closest(".encrypted.folder");
  let l1_member = (foundEncrypted ? foundEncrypted : clicked).file_meta.name;
  let l2_member = foundEncrypted ? clicked.file_meta.name : null;
  let progressContainer = createProgressContainer(
    clicked.querySelector("span")
  );
  const percentText = progressContainer.querySelector(".percent");
  let url =
    `download?` +
    `archive=${encodeURIComponent(archive)}&` +
    `l1=${encodeURIComponent(l1_member)}`;
  if (l2_member) {
    url += `&l2=${encodeURIComponent(l2_member)}`;
  }

  const isDesktopFS = "showSaveFilePicker" in window;
  try {
    if (isDesktopFS) {
      const extension =
        l2_member?.split(".").pop() || l1_member?.split(".").pop();
      const file_name =
        l2_member?.split("/").pop() || l1_member?.split("/").pop();
      const handle = await window.showSaveFilePicker({
        suggestedName: file_name,
        types: [
          {
            description: `.${extension}-file`,
            accept: { "application/octet-stream": [`.${extension}`] },
          },
        ],
      });

      const writable = await handle.createWritable();

      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      let received = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        await writable.write(value);
        received += value.length;
        const percent = Math.round((received / file_size) * 100);
        percentText.textContent = ` ${percent}%`;
      }
      percentText.textContent = ` 💾 Saving...`;
      await writable.close();
      percentText.textContent = " ✅ Done";
    } else {
      const a = document.createElement("a");
      a.href = url;
      //a.download = l2_member;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      percentText.textContent = " ⬇️ Downloading...";
      setTimeout(() => (percentText.textContent = " ✅ Done"), 2500);
    }
  } catch (err) {
    if (err.name == "AbortError") {
      percentText.textContent = " ❌ Cancelled";
    } else {
      console.error("Download error:", err);
      percentText.textContent = " ❌ Error";
    }
  } finally {
    setTimeout(() => progressContainer.remove(), 5000);
  }
}

function formatBytes(bytes, decimals = 2) {
  const k = 1024;
  const sizes = [
    "Bytes",
    "KiB",
    "MiB",
    "GiB",
    "TiB",
    "PiB",
    "EiB",
    "ZiB",
    "YiB",
  ];
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 Bytes";
  }
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const index = Math.min(i, sizes.length - 1);
  const dm = Math.max(0, decimals);
  const value = bytes / Math.pow(k, index);
  const formattedValue = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: dm,
    minimumFractionDigits: dm,
  }).format(value);
  return `${formattedValue} ${sizes[index]}`;
}

function buildTree(files) {
  const root = {};
  for (const f of files) {
    const parts = f.type == "root" ? [f.name] : f.name.split("/");
    let node = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!part) continue;
      node[part] = node[part] || (i === parts.length - 1 ? f : {});
      node = node[part];
    }
    if (f.type == "zip" || (f.files && Array.isArray(files))) {
      const arch_root = buildTree(f.files);
      for (const [name, val] of Object.entries(arch_root)) {
        node[name] = val;
      }
    }
  }
  return root;
}

function fileCount(object) {
  return Object.keys(getFsMembers(object)).length;
}

function getFsMembers(object) {
  const result = {};
  for (var key in object) {
    if (object.hasOwnProperty(key) && is_filesystem_member(object[key])) {
      result[key] = object[key];
    }
  }
  return result;
}

function is_filesystem_member(val) {
  return typeof val === "object" && !Array.isArray(val) && val !== null;
}

function renderTree(data) {
  const table = document.createElement("table");
  table.className = "file-tree";

  const thead = document.createElement("thead");
  thead.innerHTML = `
    <tr>
      <th>Name</th>
      <th>Size</th>
      <th>Date</th>
      <th>Compression</th>
    </tr>`;
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  table.appendChild(tbody);

  const fileTree = buildTree(data);
  renderRow(tbody, fileTree, 0);

  return table;
}

function renderRow(tbody, fileTree, depth) {
  const result_rows = [];
  const entries = Object.entries(getFsMembers(fileTree));
  for (let i = 0; i < entries.length; i++) {
    const [name, node] = entries[i];
    if (!is_filesystem_member(node)) continue;
    const tr = document.createElement("tr");
    tr.className = node.type === "dir" || node.files ? "folder" : "file";

    const isLast = i === entries.length - 1;
    if (isLast) tr.classList.add("last-child");
    if (node.type == "root") tr.classList.add("root");
    if (node.type == "backup") tr.classList.add("backup");

    const indent = depth * 20;

    const tdName = document.createElement("td");
    tdName.style.paddingLeft = `${indent}px`;
    tr.style.setProperty("--depth", depth);

    const clickable = document.createElement("span");
    clickable.className = "clickable";
    clickable.textContent = name;

    tdName.appendChild(clickable);
    tr.appendChild(tdName);

    const tdSize = document.createElement("td");
    tdSize.textContent = node.size ? formatBytes(node.size) : "—";
    tr.appendChild(tdSize);

    const tdDate = document.createElement("td");
    tdDate.textContent = node.mtime || "—";
    tr.appendChild(tdDate);

    const tdComp = document.createElement("td");
    tdComp.textContent = node.compression || "—";
    tr.appendChild(tdComp);

    tbody.appendChild(tr);

    // node.table_row = tr;
    node._id = Math.random().toString(36).substr(2, 9);
    tr.dataset.id = node._id;
    if (fileTree._id) {
      tr.classList.add("hidden");
      node._parent = fileTree._id;
      tr.dataset.parent = fileTree._id;
    }
    //node.root_folder = dir;
    node.depth = depth;
    tr.file_meta = node;
    tr.dataset.depth = depth;
    result_rows.push(tr);
    if (node.type !== "file") {
      const rows = renderRow(tbody, node, depth + 1);
      result_rows.push(...rows);
      clickable.addEventListener("click", () => {
        tr.classList.toggle("open");
        const isOpen = tr.classList.contains("open");
        hideChildren(depth, rows, isOpen);
      });

      if (node.type === "zip") {
        tr.classList.add("encrypted");
      }
    }
  }
  return result_rows;
}

function hideChildren(depth, rows, isOpen) {
  for (const child of rows) {
    if (isOpen && child.file_meta.depth == depth + 1) {
      child.classList.remove("hidden");
    } else if (!isOpen) {
      child.classList.add("hidden");
      child.classList.remove("open");
    }
  }
}

function attachFolderHandlers() {
  document.querySelectorAll(".folder").forEach((el) => {
    el.addEventListener("click", (e) => {
      if (e.target === el || e.target.parentElement === el) {
        el.classList.toggle("open");
      }
    });
  });
  document.querySelectorAll(".file").forEach((el) => {
    el.addEventListener("click", (e) => {
      download(e.target.closest(".file"));
    });
  });
}

window.onload = function () {
  loadTars();
};
