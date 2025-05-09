document.addEventListener("DOMContentLoaded", function() {
    const poetryInput = document.getElementById("poetry-input");
    const analyzeButton = document.getElementById("analyze-button");
    const clearButton = document.getElementById("clear-button");
    const copyButton = document.getElementById("copy-button");
    const resultsOutput = document.getElementById("results-output");

    const aboutButton = document.getElementById("about-button");
    const aboutModal = document.getElementById("about-modal");
    const closeButton = document.querySelector(".modal-content .close-button");

    if (aboutButton && aboutModal && closeButton) {
        aboutButton.onclick = function() {
            aboutModal.style.display = "block";
        }
        closeButton.onclick = function() {
            aboutModal.style.display = "none";
        }
        window.onclick = function(event) {
            if (event.target == aboutModal) {
                aboutModal.style.display = "none";
            }
        }
    }

    if (analyzeButton) {
        analyzeButton.addEventListener("click", async function() {
            let inputText = poetryInput.value.trim();
            if (!inputText) {
                resultsOutput.innerHTML = "<p>الرجاء إدخال الأبيات الشعرية أولاً.</p>";
                return;
            }

            // الحد الأقصى 10 أبيات
            const lines = inputText.split("\n");
            if (lines.length > 10) {
                inputText = lines.slice(0, 10).join("\n");
                alert("تم اقتصار الإدخال على 10 أبيات فقط.");
                poetryInput.value = inputText; // تحديث الواجهة بالإدخال المقتصر
            }
            
            resultsOutput.innerHTML = "<p>جاري التحليل...</p>";

            try {
                const response = await fetch("/analyze", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ poem: inputText })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `Server error: ${response.status}`);
                }

                const data = await response.json();
                if (data.error) {
                    resultsOutput.innerHTML = `<p style='color:red;'>خطأ: ${data.error}</p>`;
                } else {
                    resultsOutput.innerHTML = data.html_output; 
                }
            } catch (error) {
                resultsOutput.innerHTML = `<p style='color:red;'>حدث خطأ أثناء التحليل: ${error.message}</p>`;
                console.error("Error during analysis:", error);
            }
        });
    }

    if (clearButton) {
        clearButton.addEventListener("click", function() {
            poetryInput.value = "";
            resultsOutput.innerHTML = "";
        });
    }

    if (copyButton) {
        copyButton.addEventListener("click", function() {
            const textToCopy = resultsOutput.innerHTML; // ينسخ محتوى HTML
            if (textToCopy) {
                navigator.clipboard.writeText(resultsOutput.innerText) // ينسخ النص فقط
                    .then(() => {
                        alert("تم نسخ النتائج إلى الحافظة!");
                    })
                    .catch(err => {
                        console.error("خطأ في نسخ النتائج: ", err);
                        alert("فشل نسخ النتائج.");
                    });
            } else {
                alert("لا توجد نتائج لنسخها.");
            }
        });
    }
});
