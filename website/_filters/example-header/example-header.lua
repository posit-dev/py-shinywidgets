-- Renders a header bar (file link, line count, open/copy/Shinylive icons) on every
-- ```{.python file="examples/x.py" files="helper.py" collapse="true"} block, marks prose
-- links to example .py files as Shinylive links, and embeds each example's files as JSON
-- for example-header.js to turn into a shinylive.io URL.

local ICONS = {
  chevron = '<path d="m6 9 6 6 6-6"/>',
  open = '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>'
    .. '<path d="M14 3v6h6"/><path d="m10 13-2 2 2 2"/><path d="m14 17 2-2-2-2"/>',
  copy = '<rect x="9" y="9" width="12" height="12" rx="2"/>'
    .. '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  shinylive = '<polygon points="6 4 20 12 6 20 6 4"/>',
}

-- Bundle key (link target as written, fragment stripped) -> { extras = {name...}, seen = {name=true} }
local bundles = {}
local bundle_order = {}
local block_count = 0

local function svg(name)
  return '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">' .. ICONS[name] .. "</svg>"
end

local function esc(s)
  return (s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;"))
end

local function page_dir()
  return pandoc.path.directory(quarto.doc.input_file)
end

local function read_file(path)
  local fh = io.open(path, "r")
  if fh == nil then
    error("example-header: can't read " .. path .. " (from " .. quarto.doc.input_file .. ")")
  end
  local text = fh:read("a")
  fh:close()
  return text
end

local function strip_fragment(target)
  return (target:gsub("#.*$", ""))
end

-- Mirrors the example-link rule in the plan: examples/ or gallery/ .py files, or a
-- sibling page's ../<page>/examples/*.py.
local function is_example(target)
  local path = strip_fragment(target)
  if not path:match("%.py$") then
    return false
  end
  if path:match("^examples/") or path:match("^gallery/") then
    return true
  end
  return path:match("^%.%./") ~= nil and path:find("/examples/", 1, true) ~= nil
end

local function register(key, extras)
  local b = bundles[key]
  if b == nil then
    b = { extras = {}, seen = {} }
    bundles[key] = b
    table.insert(bundle_order, key)
  end
  for _, name in ipairs(extras) do
    if not b.seen[name] then
      b.seen[name] = true
      table.insert(b.extras, name)
    end
  end
end

-- Lines after trimming leading/trailing blank lines and trailing whitespace.
local function trimmed_lines(text)
  local lines = {}
  for line in (text .. "\n"):gmatch("(.-)\r?\n") do
    table.insert(lines, (line:gsub("%s+$", "")))
  end
  while #lines > 0 and lines[#lines] == "" do
    table.remove(lines)
  end
  while #lines > 0 and lines[1] == "" do
    table.remove(lines, 1)
  end
  return lines
end

local function plural(n)
  return n == 1 and "1 line" or (n .. " lines")
end

local function meta_text(block_text, file_text)
  local block = trimmed_lines(block_text)
  local file = trimmed_lines(file_text)
  local same = #block == #file
  if same then
    for i = 1, #block do
      if block[i] ~= file[i] then
        same = false
        break
      end
    end
  end
  if same then
    return plural(#file)
  end
  return "excerpt · " .. #block .. " of " .. plural(#file)
end

local function split_words(s)
  local words = {}
  for w in (s or ""):gmatch("%S+") do
    table.insert(words, w)
  end
  return words
end

local function bar_html(key, extras, meta, collapsed, code_id)
  local dir = pandoc.path.directory(key)
  local parts = {
    '<div class="sw-example-bar">',
    string.format(
      '<button type="button" class="sw-example-toggle" aria-expanded="%s" aria-controls="%s" aria-label="Toggle code">%s</button>',
      collapsed and "false" or "true",
      code_id,
      svg("chevron")
    ),
    string.format('<a class="sw-example-file" href="%s">%s</a>', esc(key), esc(key)),
  }
  for _, name in ipairs(extras) do
    local href = dir == "." and name or pandoc.path.join({ dir, name })
    table.insert(parts, string.format('<a class="sw-example-extra" href="%s">+ %s</a>', esc(href), esc(name)))
  end
  table.insert(parts, '<span class="sw-example-meta">' .. esc(meta) .. "</span>")
  table.insert(parts, '<span class="sw-example-actions">')
  table.insert(
    parts,
    string.format(
      '<a class="sw-example-action" data-action="open" href="%s" target="_blank" rel="noopener" title="Open %s" aria-label="Open %s">%s</a>',
      esc(key),
      esc(key),
      esc(key),
      svg("open")
    )
  )
  table.insert(
    parts,
    '<button type="button" class="sw-example-action" data-action="copy" title="Copy code" aria-label="Copy code">'
      .. svg("copy")
      .. "</button>"
  )
  table.insert(
    parts,
    string.format(
      '<a class="sw-example-action" data-action="shinylive" href="%s" data-example="%s" title="Open in Shinylive" aria-label="Open in Shinylive">%s</a>',
      esc(key),
      esc(key),
      svg("shinylive")
    )
  )
  table.insert(parts, "</span></div>")
  return table.concat(parts)
end

local function code_block(cb)
  local target = cb.attributes["file"]
  if target == nil then
    return nil
  end
  local key = strip_fragment(target)
  local extras = split_words(cb.attributes["files"])
  local collapsed = cb.attributes["collapse"] == "true"
  cb.attributes["file"] = nil
  cb.attributes["files"] = nil
  cb.attributes["collapse"] = nil
  register(key, extras)

  block_count = block_count + 1
  local code_id = "sw-ex-" .. block_count
  local file_text = read_file(pandoc.path.join({ page_dir(), key }))
  local classes = { "sw-example" }
  if collapsed then
    table.insert(classes, "sw-collapsed")
  end
  return pandoc.Div({
    pandoc.RawBlock("html", bar_html(key, extras, meta_text(cb.text, file_text), collapsed, code_id)),
    pandoc.Div({ cb }, pandoc.Attr(code_id, { "sw-example-code" })),
  }, pandoc.Attr("", classes, { ["data-example"] = key }))
end

local function link(el)
  -- An explicit {.sw-shinylive-link} opts any .py target in (e.g. a showcase's
  -- app.py); otherwise only example paths qualify.
  local explicit = el.classes:find("sw-shinylive-link") ~= nil
  if not explicit and not is_example(el.target) then
    return nil
  end
  local key = strip_fragment(el.target)
  register(key, {})
  if not explicit then
    table.insert(el.classes, "sw-shinylive-link")
  end
  el.attributes["data-example"] = key
  return el
end

local function requirements(meta)
  local reqs = meta["shinylive-requirements"]
  if reqs ~= nil and pandoc.utils.type(reqs) == "List" then
    local lines = {}
    for _, r in ipairs(reqs) do
      table.insert(lines, pandoc.utils.stringify(r))
    end
    return table.concat(lines, "\n") .. "\n"
  end
  if meta.extra ~= nil then
    return pandoc.utils.stringify(meta.extra) .. "\n"
  end
  -- Showcase pages ship their own requirements.txt next to app.py.
  local path = pandoc.path.join({ page_dir(), "requirements.txt" })
  local fh = io.open(path, "r")
  if fh ~= nil then
    local text = fh:read("a")
    fh:close()
    if text:sub(-1) ~= "\n" then
      text = text .. "\n"
    end
    return text
  end
  return "shinywidgets\n"
end

local function finish(doc)
  if #bundle_order == 0 then
    return nil
  end
  local reqs = requirements(doc.meta)
  local out = {}
  for _, key in ipairs(bundle_order) do
    local main = pandoc.path.join({ page_dir(), key })
    local files = { { name = "app.py", content = read_file(main) } }
    local main_dir = pandoc.path.directory(main)
    for _, name in ipairs(bundles[key].extras) do
      table.insert(files, { name = name, content = read_file(pandoc.path.join({ main_dir, name })) })
    end
    table.insert(files, { name = "requirements.txt", content = reqs })
    out[key] = files
  end
  -- "</" can't appear raw inside <script>; "<\/" is the same string to JSON.
  local json = quarto.json.encode(out):gsub("</", "<\\/")
  doc.blocks:insert(pandoc.RawBlock("html", '<script type="application/json" id="sw-example-bundles">' .. json .. "</script>"))
  quarto.doc.add_html_dependency({
    name = "sw-example-header",
    version = "1.0.0",
    scripts = { "lz-string.min.js", "example-header.js" },
  })
  return doc
end

return {
  { CodeBlock = code_block, Link = link },
  { Pandoc = finish },
}
